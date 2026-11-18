"""N32 / QĐ28: CPU unit tests for the exact APTOS training notebook.

From the repository root:
    python -m pytest test/test_aptos_mvp.py -v --tb=short
To test a different notebook, set APTOS_NOTEBOOK to its path.
No APTOS images, pretrained weights, or GPU are needed.
"""
import json
import os
from pathlib import Path

import numpy as np
import pytest
import torch
import torch.nn as nn
import torch.nn.functional as F


@pytest.fixture(scope="module")
def app():
    repo = Path(__file__).resolve().parent.parent
    path = Path(os.environ.get("APTOS_NOTEBOOK", repo / "notebooks/aptos/baselines/code-fixed.ipynb"))
    assert path.is_file(), f"Missing notebook: {path} (set APTOS_NOTEBOOK)"
    nb = json.loads(path.read_text(encoding="utf-8-sig"))
    scope = {"__name__": "aptos_test", "__cells__": nb["cells"]}
    # Import notebook's OWN definitions without executing main() or loading APTOS.
    for i in (1, 2, 3, 4, 5, 6, 11):
        source = nb["cells"][i]["source"]
        if isinstance(source, list):
            source = "".join(source)
        exec(compile(source, f"{path.name}:cell{i}", "exec"), scope)
    return scope


def test_losses_forward_backward_and_extreme_logits(app):
    torch.manual_seed(42)
    counts = [7, 5, 3, 2, 1]
    for method in app["METHODS"]:
        hp = app["parameter_grid"](method)[0]
        ctx = app["LossContext"](method, counts, hp).double()
        nlogits = 4 if method == "CORN" else 5
        y = torch.tensor([0, 1, 2, 3, 4], dtype=torch.long)
        for mult in (1.0, 1000.0):
            z = (torch.randn(5, nlogits, dtype=torch.float64) * mult).requires_grad_()
            value, _ = ctx(z, y)
            grad, = torch.autograd.grad(value, z)
            assert torch.isfinite(value) and torch.isfinite(grad).all(), method


def test_gradcheck_nine_losses(app):
    torch.manual_seed(3)
    counts = [7, 5, 3, 2, 1]
    y = torch.tensor([0, 2, 4])
    for method in ("A0", "A3", "A4", "A6", "A8", "A9", "A11", "SLACE", "CORN"):
        ctx = app["LossContext"](method, counts, app["parameter_grid"](method)[0]).double()
        z = torch.randn(3, 4 if method == "CORN" else 5, dtype=torch.float64, requires_grad=True)
        assert torch.autograd.gradcheck(lambda a: ctx(a, y)[0], (z,), eps=1e-6, atol=1e-4), method


def test_a12_stop_gradient(app):
    torch.manual_seed(7)
    y = torch.tensor([0, 1, 2, 3, 4])
    z = torch.randn(5, 5, dtype=torch.float64, requires_grad=True)
    ctx = app["LossContext"]("A12", [7, 5, 3, 2, 1], app["parameter_grid"]("A12")[0]).double()
    value, _ = ctx(z, y)
    lp, ordinal, _, d = app["ordinal_parts"](z, y)
    focal = app["focal_vector"](lp, y, ctx.w, ctx.hp["gamma"])
    lam = ctx.hp["alpha"] * ctx.w[y] * d
    expected = (focal + lam.detach() * ordinal).mean()
    alternative = (focal + lam * ordinal).mean()
    got_grad = torch.autograd.grad(value, z, retain_graph=True)[0]
    expected_grad = torch.autograd.grad(expected, z, retain_graph=True)[0]
    alternative_grad = torch.autograd.grad(alternative, z)[0]
    assert torch.allclose(got_grad, expected_grad, atol=1e-10)
    assert not torch.allclose(got_grad, alternative_grad)


def test_sqrt_weights_and_a8_fixed_lambda(app):
    counts = [7, 5, 3, 2, 1]
    w = app["class_weights"](counts, 0.999, True, dtype=torch.float64)
    effective = (1 - 0.999) / (1 - np.power(0.999, counts))
    ref_w = 5 * np.sqrt(effective) / np.sqrt(effective).sum()
    assert np.allclose(w.numpy(), ref_w)
    z = torch.randn(5, 5, dtype=torch.float64)
    y = torch.arange(5)
    ctx = app["LossContext"]("A8", counts, {**app["parameter_grid"]("A8")[0], "lambda": 0.3}).double()
    lp, ordinal, _, _ = app["ordinal_parts"](z, y)
    expected = (app["focal_vector"](lp, y, ctx.w, ctx.hp["gamma"]) + 0.3 * ordinal).mean()
    assert torch.allclose(ctx(z, y)[0], expected)


def test_slace_author_style_proximity_loss_and_gradient(app):
    # Independent loop reference following SLACE authors' 'prox' and 'max' accumulation.
    # Source: https://github.com/inbarnachmani/SLACE (losses.py, utils.py)
    counts = [7, 5, 3, 2, 1]
    k = len(counts)
    prox = torch.empty(k, k, dtype=torch.float64)
    for i in range(k):
        for j in range(k):
            lo, hi = min(i, j), max(i, j)
            mass = counts[i] / 2 + sum(counts[t] for t in range(lo, hi + 1) if t != i)
            prox[i, j] = -np.log(mass / sum(counts))
    rank_masks = []
    for target in range(k):
        order = prox[:, target].argsort().flip(0).tolist()
        rank_masks.append(torch.tensor([[order.index(j) <= order.index(i) for j in range(k)] for i in range(k)]))
    masks = torch.stack(rank_masks)
    torch.manual_seed(8)
    y = torch.tensor([0, 1, 2, 3, 4])
    for alpha in (0.3, 1.0, 10.0):
        z = torch.randn(5, 5, dtype=torch.float64, requires_grad=True)
        p = z.softmax(1)
        soft = torch.softmax(alpha * prox.T[y], 1)
        accum = torch.einsum("nij,nj->ni", masks[y].double(), p)
        reference = -(soft * accum.log()).sum(1).mean()
        model = app["LossContext"]("SLACE", counts, {"alpha": alpha}).double()(z, y)[0]
        assert torch.allclose(model, reference, atol=1e-9), alpha
        assert torch.allclose(torch.autograd.grad(model, z, retain_graph=True)[0],
                              torch.autograd.grad(reference, z)[0], atol=1e-9), alpha


def test_corn_reference_loss_and_decoding(app):
    torch.manual_seed(3)
    z = torch.randn(5, 4, dtype=torch.float64, requires_grad=True)
    y = torch.tensor([0, 1, 2, 3, 4])
    numerator = 0
    denominator = 0
    for j in range(4):
        eligible = y >= j
        numerator = numerator + F.binary_cross_entropy_with_logits(z[eligible, j], (y[eligible] > j).double(), reduction="sum")
        denominator += int(eligible.sum())
    ctx = app["LossContext"]("CORN", [7, 5, 3, 2, 1], {}).double()
    got = ctx(z, y)[0]
    ref = numerator / denominator
    assert torch.allclose(got, ref, atol=1e-12)
    assert torch.allclose(torch.autograd.grad(got, z, retain_graph=True)[0], torch.autograd.grad(ref, z)[0])
    conditional = torch.tensor([[0.9, 0.8 / 0.9, 0.3 / 0.8, 0.1 / 0.3], [0.1, 0.5, 0.5, 0.5],
                                [0.99, 0.99, 0.99, 0.99]], dtype=torch.float64)
    assert app["corn_decode"](torch.logit(conditional)).tolist() == [2, 0, 4]


def test_global_average_pool_output_and_gradient(app):
    x = torch.randn(2, 3, 4, 5, dtype=torch.float64, requires_grad=True)
    got = app["GlobalAvgPool"]()(x)
    ref = nn.AdaptiveAvgPool2d(1)(x)
    assert torch.allclose(got, ref, atol=1e-14)
    assert torch.allclose(torch.autograd.grad(got.sum(), x, retain_graph=True)[0],
                          torch.autograd.grad(ref.sum(), x)[0])


def test_batchnorm_freeze_preserves_affine_gradients(app):
    for frozen in (True, False):
        bn = nn.BatchNorm2d(3)
        model = nn.Sequential(bn, nn.Conv2d(3, 3, 1))
        before = bn.running_mean.clone()
        app["train_mode"](model, frozen)
        model(torch.ones(4, 3, 8, 8) * 2).sum().backward()
        assert torch.equal(bn.running_mean, before) == frozen
        assert bn.weight.requires_grad and bn.weight.grad is not None


def test_augmentation_determinism(app):
    app["CACHE"] = {"fixture": np.arange(60*60*3, dtype=np.uint8).reshape(60, 60, 3)}
    app["RUN_SEED"] = 42
    import pandas as pd
    s0 = {"images": pd.DataFrame({"grade": [2]}, index=["fixture"])}
    ds = app["FundusDataset"](["fixture"], s0, True)
    x1 = ds[(0, 7)][0]
    assert torch.equal(x1, ds[(0, 7)][0])
    assert not torch.equal(x1, ds[(0, 8)][0])
    val = app["FundusDataset"](["fixture"], s0, False)
    assert torch.equal(val[(0, 7)][0], val[(0, 8)][0])


def test_boundary_and_batchnorm_selection(app):
    candidate = app["boundary_candidate"]("A8", {"lambda": 0.1})
    assert candidate["lambda"] == pytest.approx(0.1 / 3)
    candidate = app["boundary_candidate"]("A8", {"lambda": 10.0})
    assert candidate["lambda"] == pytest.approx(30)
    assert app["boundary_candidate"]("A8", {"lambda": 0.3}) is None
    assert app["choose_batchnorm"]({"true": 0.8, "false": 0.805}) is True
    assert app["choose_batchnorm"]({"true": 0.8, "false": 0.82}) is False


def test_s0_approval_gate_exists(app):
    # Verify the FULL_TRAIN gate is present without loading APTOS data.
    source = app["__cells__"][3]["source"]
    if isinstance(source, list):
        source = "".join(source)
    assert "MODE == 'FULL_TRAIN'" in source
    for field in ("approved_frozen", "official", "advisor_approval_ref"):
        assert field in source
