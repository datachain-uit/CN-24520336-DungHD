"""N33: AMP overflow regression checks against the REAL APTOS train_epoch.

From repository root on Kaggle T4 x2:
    python -m pytest test/test_amp_overflow.py -v -s --tb=short \
        -p no:cacheprovider

The CPU test is a regression smoke test; the CUDA test is the required N33
GPU evidence. It forces overflow with init_scale=2**40, then verifies recovery.
No APTOS dataset, pretrained weights, or FULL_TRAIN run are needed.
"""
import json
import os
from pathlib import Path

import pytest
import torch
from torch import nn


@pytest.fixture(scope='module')
def app():
    repo = Path(__file__).resolve().parent.parent
    path = Path(os.environ.get('APTOS_NOTEBOOK', repo / 'notebooks/aptos/baselines/code-fixed.ipynb'))
    assert path.is_file(), f'Notebook not found: {path} (set APTOS_NOTEBOOK)'
    nb = json.loads(path.read_text(encoding='utf-8-sig'))
    scope = {'__name__': 'aptos_amp_test'}
    # Real notebook functions; do not execute main, load_s0 or training on APTOS.
    for i in (1, 2, 4, 5, 7):
        cell = nb['cells'][i]['source']
        source = ''.join(cell) if isinstance(cell, list) else cell
        exec(compile(source, f'{path.name}:cell{i}', 'exec'), scope)
    return scope


def _make_test_run(app, device, initial_scale, batch_list, use_dp=False):
    torch.manual_seed(42)
    app['DEVICE'] = torch.device(device)
    app['CFG']['amp'] = device.startswith('cuda')
    model = nn.Sequential(nn.Linear(4, 16), nn.ReLU(), nn.Linear(16, 5)).to(device)
    if use_dp:
        model = nn.DataParallel(model, device_ids=[0, 1])
    criterion = app['LossContext']('A0', [8, 8, 8, 8, 8], {}).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
    scaler = torch.amp.GradScaler('cuda' if device.startswith('cuda') else 'cpu', init_scale=initial_scale)
    assert scaler.is_enabled(), 'The test must use an enabled GradScaler'
    before = [p.detach().clone() for p in model.parameters()]
    result = app['train_epoch'](model, criterion, optimizer, scaler, batch_list, frozen=False)
    changed = any(not torch.equal(old, p.detach()) for old, p in zip(before, model.parameters()))
    return result, scaler, changed, model, criterion, optimizer


def test_amp_overflow_cpu_smoke(app):
    """CPU: provokes nonfinite *scaled gradients*, not a nonfinite forward loss."""
    huge = (torch.full((8, 4), 1e30), torch.tensor([0, 1, 2, 3, 4, 0, 1, 2]), ['high'] * 8)
    normal = (torch.randn(8, 4), torch.tensor([0, 1, 2, 3, 4, 0, 1, 2]), ['normal'] * 8)
    result, scaler, changed, _, _, _ = _make_test_run(app, 'cpu', 2.0**40, [huge, normal])
    assert result['steps'] == 2
    assert result['amp_overflow_steps'] >= 1
    assert scaler.get_scale() < 2.0**40
    print(f'CPU overflow smoke PASS: overflow={result["amp_overflow_steps"]}/2, '
          f'scale_after={scaler.get_scale():.3g}, weights_changed={changed}')


@pytest.mark.skipif(not torch.cuda.is_available() or torch.cuda.device_count() < 2,
                    reason='Requires Kaggle GPU T4 x2; CPU smoke does not replace GPU evidence')
def test_amp_overflow_cuda_t4x2(app):
    """CUDA: force FP16 overflow, validate skip+scale decrease, then a normal update."""
    device = 'cuda:0'
    labels = torch.tensor([0, 1, 2, 3, 4, 0, 1, 2] * 4)
    batches = [(torch.randn(32, 4), labels.clone(), ['synthetic'] * 32) for _ in range(2)]
    result, scaler, _, model, criterion, optimizer = _make_test_run(
        app, device, 2.0**40, batches, use_dp=True
    )
    assert result['steps'] == 2
    assert result['amp_overflow_steps'] >= 1, 'High initial loss scale did not produce overflow'
    assert scaler.get_scale() < 2.0**40, 'GradScaler did not reduce scale after overflow'

    # Confirm model and optimizer remain usable after the forced overflow.
    before = [p.detach().clone() for p in model.parameters()]
    recovery_scaler = torch.amp.GradScaler('cuda', init_scale=128.0)
    recovered = app['train_epoch'](model, criterion, optimizer, recovery_scaler, batches, frozen=False)
    assert recovered['amp_overflow_steps'] == 0, 'Unexpected overflow at normal scale'
    assert any(not torch.equal(p, old) for p, old in zip(model.parameters(), before)), \
        'Model weights were not updated after recovery'
    print('GPU N33 PASS: device0=' + torch.cuda.get_device_name(0) +
          ', device1=' + torch.cuda.get_device_name(1) +
          f', overflow={result["amp_overflow_steps"]}/2, '
          f'scale_after={scaler.get_scale():.3g}, recovery_overflow=0/2, weights_updated=yes')
