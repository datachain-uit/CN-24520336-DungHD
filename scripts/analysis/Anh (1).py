# -*- coding: utf-8 -*-
"""
Ve 21 hinh minh hoa cho bao cao UTKFace A12, phu hop cay thu muc Sqrt/NoSqrt.

Su dung:
    python Anh.py
    python Anh.py --images "D:\\NCKH\\UTKFace"

Anh se duoc tao tu dong tai ROOT/Anh (co the thay bang --out).
Khong sinh du lieu gia: hinh nao thieu du lieu chi tiet se SKIP va ghi ly do.
"""
from __future__ import annotations

import argparse
import ast
import csv
import json
import math
import os
import re
import sys
import traceback
from collections import defaultdict
from pathlib import Path

try:
    import numpy as np
    import pandas as pd
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MultipleLocator
except ImportError as exc:
    print('Thieu thu vien:', exc)
    print('Cai dat: python -m pip install numpy pandas matplotlib pillow openpyxl')
    raise SystemExit(2)

REPORT_TITLES = {1: 'QWK va Macro F1 cua 18 cau hinh', 2: 'Reliability diagram (15 bins)', 3: 'Confidence cua du doan dung va sai', 4: 'Danh doi QWK va NLL', 5: 'Doi chieu A1 A2 A3 va A12', 6: 'QWK validation va test theo lambda', 7: 'Do nhay cua lambda theo nhieu muc tieu', 8: 'Chenh lech ablation theo tung seed', 9: 'Tinh nhat quan tren nhieu chi so', 10: 'A5 A7 va A12: he so ordinal', 11: 'Bo trong so lop o C hoac O', 12: 'Vai tro focal va stop-gradient', 13: 'Sqrt va NoSqrt ghep cap theo seed', 14: 'Phan ra khoang cach loi', 15: 'Trong so lop va muc khop train', 16: 'F1 theo lop va so anh', 17: 'Ma tran nham lan NoSqrt', 18: 'Anh minh hoa loi va confidence', 19: 'Bien thien giua ba seed', 20: 'Duong hoc tai checkpoint tot nhat', 21: 'Chat luong so voi thoi gian huan luyen'}

PLT = plt
plt.rcParams.update({
    'font.family': 'DejaVu Sans', 'font.size': 10,
    'axes.titlesize': 11, 'axes.labelsize': 10,
    'axes.spines.top': False, 'axes.spines.right': False,
    'figure.dpi': 110, 'savefig.dpi': 300,
    'savefig.bbox': 'tight', 'axes.grid': False,
})

METRICS = {
    'qwk': ['qwk', 'quadratic_weighted_kappa', 'quadratic_kappa'],
    'group_mae': ['group_mae', 'mae', 'mean_absolute_error', 'mae_group'],
    'accuracy': ['accuracy', 'acc'],
    'f1_macro': ['f1_macro', 'macro_f1', 'f1score_macro', 'macro_f1_score'],
    'ece15': ['ece15', 'ece_15', 'ece_15_bins', 'ece', 'expected_calibration_error'],
    'nll': ['nll', 'negative_log_likelihood'],
    'brier_multiclass': ['brier_multiclass', 'brier', 'brier_score'],
    'within1': ['within1', 'within_1', 'within_one'],
    'within2': ['within2', 'within_2', 'within_two'],
    'training_hours': ['training_hours', 'train_time_hours', 'train_duration_hours'],
    'best_epoch': ['best_epoch'],
    'recall_macro': ['recall_macro', 'macro_recall'],
    'precision_macro': ['precision_macro', 'macro_precision'],
}
LOWER = {'group_mae', 'nll', 'ece15', 'brier_multiclass'}
LAMBDA = {'A4_1': .03, 'A4_2': .05, 'A4_3': .1,
          'A4_4': .3, 'A4_5': .5, 'A4_6': 1., 'A4_7': 3.}
ABLS = ['A7', 'A8', 'A6', 'A5', 'A3', 'A9', 'A4_5', 'A10', 'A11', 'A1', 'A2']
AGES = ['0-9', '10-19', '20-29', '30-39', '40-49', '50-59', '60-69', '70+']
COLORS = {'A1': '#3569A7', 'A2': '#D38732', 'A3': '#78868D',
          'A12': '#19826A', 'NoSqrt': '#B14B69', 'A5': '#5973A5',
          'A7': '#BA7234', 'A6': '#8777B9', 'A10': '#D18A47',
          'A8': '#7D8A94', 'A9': '#6F609D', 'A11': '#BD8260'}


def name_key(s):
    return re.sub(r'[^a-z0-9]+', '_', str(s).strip().lower()).strip('_')


def method_name(raw):
    s = str(raw).upper().replace(' ', '').replace('-', '_')
    if 'NOSQRT' in s or 'NO_SQRT' in s or 'NO-SQRT' in str(raw).upper():
        return 'NoSqrt'
    m = re.search(r'(?<![A-Z0-9])A(\d{1,2})(?:[_-]?(\d))?(?!\d)', s)
    if m:
        return 'A' + m.group(1) + ('_' + m.group(2) if m.group(2) else '')
    return str(raw).strip()


def find_col(df, candidates):
    keys = {name_key(c): c for c in df.columns}
    for candidate in candidates:
        if name_key(candidate) in keys:
            return keys[name_key(candidate)]
    return None


def num(v):
    try:
        if isinstance(v, str):
            v = v.strip().replace(',', '.')
        return float(v)
    except (TypeError, ValueError):
        return float('nan')


def nansafe_mean(vals):
    vals = np.asarray(vals, dtype=float)
    return float(np.nanmean(vals)) if np.isfinite(vals).any() else float('nan')


def read_table(p):
    p = Path(p)
    if p.suffix.lower() == '.xlsx':
        return pd.read_excel(p)
    # A one-column CSV (e.g. train labels) must NOT be auto-split by pandas sep=None.
    # The previous implementation inferred a nonsense separator from its rows.
    for encoding in ['utf-8-sig','utf-8','cp1252']:
        try:
            with p.open('r',encoding=encoding,newline='') as f:
                header = f.readline()
            sep = '\t' if header.count('\t') > header.count(',') and header.count('\t') > 0 else \
                  ';' if header.count(';') > header.count(',') and header.count(';') > 0 else ','
            return pd.read_csv(p,encoding=encoding,sep=sep,low_memory=False)
        except (UnicodeError,pd.errors.ParserError):
            continue
    raise RuntimeError(f'Khong doc duoc bang: {p}')


def get_listpaths(root):
    found = []
    ignore = {'.venv', 'venv', '.git', '__pycache__', 'node_modules', 'Anh', 'site-packages'}
    for base, ds, fs in os.walk(root):
        ds[:] = [d for d in ds if d not in ignore and not d.startswith('.ipynb_checkpoints')]
        for f in fs:
            if Path(f).suffix.lower() in ('.csv', '.xlsx', '.json', '.jsonl', '.parquet', '.npz'):
                found.append(Path(base) / f)
    return found


def get_path(paths, basenames, prefer=None):
    bs = {s.lower() for s in basenames}
    ps = [p for p in paths if p.name.lower() in bs]
    if not ps:
        return None
    if prefer:
        ps.sort(key=lambda p: (0 if prefer in str(p.parent).lower() else 1, len(str(p))))
    else:
        ps.sort(key=lambda p: len(str(p)))
    return ps[0]


def read_json_small(path, max_mb=100):
    path = Path(path)
    if path.stat().st_size > max_mb * 1024**2:
        return None
    with path.open('r', encoding='utf-8-sig') as f:
        return json.load(f)


def reshape_wide_splits(df):
    if find_col(df, ['split', 'dataset', 'phase', 'partition']):
        return df
    pref = ['test_', 'val_', 'valid_', 'validation_', 'train_']
    cols = [c for c in df.columns if any(name_key(c).startswith(p) for p in pref)
            and name_key(c) not in {'train_hours','train_minutes','train_time','train_duration','train_seconds'}]
    if not cols:
        df = df.copy()
        df['split'] = 'test'
        return df
    shared = [c for c in df.columns if c not in cols]
    out = []
    for split, prefixes in [('test', ['test_']), ('val', ['val_', 'valid_', 'validation_']),
                            ('train', ['train_'])]:
        subcols = []
        ren = {}
        for c in cols:
            low = name_key(c)
            for p in prefixes:
                if low.startswith(p):
                    subcols.append(c)
                    ren[c] = low[len(p):]
                    break
        if subcols:
            temp = df[shared + subcols].rename(columns=ren).copy()
            temp['split'] = split
            out.append(temp)
    return pd.concat(out, ignore_index=True) if out else df


def normalize_runs(df, default_method=None, default_split='test'):
    if df is None or len(df) == 0:
        return pd.DataFrame()
    df = reshape_wide_splits(df)
    mc = find_col(df, ['method', 'experiment', 'exp', 'experiment_id', 'ablation', 'method_id',
                       'variant', 'config', 'model', 'loss_name', 'run_name', 'name'])
    sc = find_col(df, ['seed', 'random_seed', 'rng_seed'])
    split = find_col(df, ['split', 'dataset', 'phase', 'partition'])
    if mc is None and default_method is None:
        return pd.DataFrame()
    out = pd.DataFrame(index=df.index)
    out['method'] = df[mc].map(method_name) if mc else default_method
    out['seed'] = pd.to_numeric(df[sc], errors='coerce') if sc else np.nan
    out['split'] = (df[split].astype(str).str.lower().str.strip()
                    if split else default_split)
    out['split'] = out['split'].replace({'valid': 'val', 'validation': 'val', 'testing': 'test', 'training': 'train'})
    for metric, aliases in METRICS.items():
        c = find_col(df, aliases)
        if c is not None:
            out[metric] = pd.to_numeric(df[c], errors='coerce')
    for c in ['method', 'seed', 'split']:
        if c not in out:
            return pd.DataFrame()
    # Chuan hoa gia tri seed thanh int de join giua cac file.
    out = out.dropna(subset=['seed']).copy()
    out['seed'] = out['seed'].astype(int)
    out = out[out['method'].notna()]
    return out.reset_index(drop=True)


def summary(d, metric, methods=None, split='test'):
    if d is None or d.empty or metric not in d:
        return pd.DataFrame(columns=['method', 'mean', 'sd', 'n'])
    sel = d[d['split'] == split].copy()
    if methods is not None:
        sel = sel[sel['method'].isin(methods)]
    g = sel.groupby('method')[metric].agg(['mean', 'std', 'count']).reset_index()
    return g.rename(columns={'std': 'sd', 'count': 'n'})


def val(d, method, seed, metric, split='test'):
    if d is None or d.empty or metric not in d:
        return np.nan
    q = d[(d['method'] == method) & (d['seed'] == seed) & (d['split'] == split)][metric]
    return float(q.iloc[0]) if len(q) else np.nan


def paired(d, method, baseline='A12', metric='qwk', higher=True):
    if metric not in d:
        return np.empty(0)
    seeds = sorted(set(d.loc[(d.method == method) & (d.split == 'test'), 'seed'])
                   & set(d.loc[(d.method == baseline) & (d.split == 'test'), 'seed']))
    pairs = []
    for seed in seeds:
        a = val(d, baseline, seed, metric)
        b = val(d, method, seed, metric)
        if np.isfinite(a) and np.isfinite(b):
            pairs.append((a-b) if higher else (b-a))
    return np.asarray(pairs)


def style_axis(ax):
    ax.grid(True, color='#e5e9ed', lw=.65, axis='y', alpha=.8)
    ax.set_axisbelow(True)


def save(fig, ctx, i, title):
    name = f'Hinh_{i:02d}.png'
    path = ctx.out / name
    fig.savefig(path, dpi=300, facecolor='white', bbox_inches='tight')
    plt.close(fig)
    ctx.success.append((i, name, REPORT_TITLES.get(i,title)))
    print(f'[OK] {name}: {REPORT_TITLES.get(i,title)}')


def fail_if(cond, reason):
    if cond:
        raise ValueError(reason)


def plot_dot(ax, df, metric, methods, label=None, use_sd=True):
    for i, m in enumerate(methods):
        sel = df[(df.method == m) & (df.split == 'test')]
        if metric not in sel:
            continue
        v = sel[metric].dropna().to_numpy(dtype=float)
        if not len(v):
            continue
        jitter = np.linspace(-.12, .12, len(v)) if len(v) > 1 else [0]
        ax.scatter(np.full(len(v), i) + jitter, v, s=18, alpha=.58, c=COLORS.get(m, '#627A93'), zorder=2)
        sd = np.std(v, ddof=1) if len(v) > 1 else 0
        ax.errorbar(i, v.mean(), yerr=(sd if use_sd else 0), color='#20262A',
                    fmt='D', markersize=5, capsize=4, lw=1.2, zorder=3)
    ax.set_xticks(np.arange(len(methods)), methods, rotation=40, ha='right')
    ax.set_title(label or metric)
    style_axis(ax)


# ---------- Readers for the actual A0-A12(Sqrt) / A12(NoSqrt) tree ----------
METHODS_MAIN = {'A1','A2','A3','A4_1','A4_2','A4_3','A4_4',
                'A4_5','A4_6','A4_7','A5','A6','A7','A8','A9','A10','A11','A12'}

def source_variant(path):
    """A12_s42 occurs in BOTH experiments: do not identify by run basename."""
    z = str(path).lower().replace(' ', '')
    if '(nosqrt)' in z or 'no_sqrt' in z or 'nosqrt' in z:
        return 'NoSqrt'
    if '(sqrt)' in z or 'utkface_a12_3seeds' in z:
        return 'Sqrt'
    return None


def run_identity(path):
    for node in [path, *path.parents]:
        m = re.fullmatch(r'(A(?:\d{1,2})(?:_\d)?)_s(\d+)', node.name, re.I)
        if m:
            method, seed = method_name(m.group(1)), int(m.group(2))
            return ('NoSqrt' if source_variant(path)=='NoSqrt' else method), seed
    return None, None


def deep_numeric(obj, names):
    """Find scalar metric without loading large all_results.json."""
    names = {name_key(x) for x in names}
    def look(x, level):
        if not isinstance(x, dict) or level > 5:
            return float('nan')
        for k,v in x.items():
            if name_key(k) in names and isinstance(v, (int,float)) and not isinstance(v,bool):
                return float(v)
        for k,v in x.items():
            if isinstance(v, dict):
                z=look(v, level+1)
                if np.isfinite(z):return z
        return float('nan')
    return look(obj,0)


def get_json_metrics(folder, split):
    p = folder / f'{split}_metrics.json'
    if not p.exists():return None
    obj=read_json_small(p, max_mb=15)
    if not isinstance(obj,dict):return None
    record={}
    for metric,keys in METRICS.items():
        v=deep_numeric(obj, [metric,*keys])
        if np.isfinite(v):record[metric]=v
    return record


def extract_json_run_rows(root):
    rows=[]
    for p in root.rglob('test_metrics.json'):
        method, seed = run_identity(p)
        if method is None or (method not in METHODS_MAIN and method != 'NoSqrt'):
            continue
        folder=p.parent
        done=folder/'done.json'
        d={}
        if done.exists():
            try:d=read_json_small(done,max_mb=15) or {}
            except Exception:pass
        for sp in ['test','val','train']:
            metrics=get_json_metrics(folder,sp)
            if not metrics:continue
            row={'method':method,'seed':seed,'split':sp,**metrics}
            for k in ['training_hours','best_epoch']:
                if k not in row:
                    row[k]=deep_numeric(d,[k,*METRICS.get(k,[])])
            # Do not mistake evaluation_seconds for training_hours
            if not np.isfinite(row.get('training_hours',np.nan)):
                mins=deep_numeric(d,['training_minutes','train_minutes'])
                if np.isfinite(mins):row['training_hours']=mins/60
            rows.append(row)
    return pd.DataFrame(rows)


def merge_runs(primary, supplement):
    if primary.empty:return supplement.copy()
    if supplement.empty:return primary.copy()
    a=primary.copy()
    b=supplement.copy()
    # Distinguish PRIMARY main summary from run JSON: primary wins for existing values.
    for col in set(a.columns).union(b.columns):
        if col not in a:a[col]=np.nan
        if col not in b:b[col]=np.nan
    a=a.drop_duplicates(['method','seed','split'],keep='first')
    b=b.drop_duplicates(['method','seed','split'],keep='first')
    x=a.set_index(['method','seed','split'])
    y=b.set_index(['method','seed','split'])
    return x.combine_first(y).reset_index()


def read_npz_pred(path):
    """Read 8-class per-image predictions, never invent labels or IDs."""
    method, seed=run_identity(path)
    if method is None:return pd.DataFrame()
    try:
        with np.load(path,allow_pickle=False) as ar:
            keys=list(ar.files)
            norm={name_key(k):k for k in keys}
            def obtain(names):
                for k in names:
                    if name_key(k) in norm:return np.asarray(ar[norm[name_key(k)]])
                return None
            yt=obtain(['y_true','true','labels','targets','target','gt','true_labels','true_classes','y_test','y'])
            yp=obtain(['y_pred','pred','preds','predictions','pred_labels','predicted','pred_classes','predictions_argmax'])
            probs=obtain(['probs','probabilities','y_prob','y_proba','softmax','prob','class_probs','y_probs','test_probs'])
            logits=obtain(['logits','scores'])
            cache_idxs=obtain(['cache_index','cache_idx'])
            try:
                ids=obtain(['image_ids','image_id','ids','filenames','file_names','paths','image_paths','names','sample_ids','filepaths','img_ids'])
            except ValueError:
                # Some producers save object-typed filenames; they require pickle.
                # Keep the valid numerical predictions; only image montage will need IDs.
                ids=None
    except Exception as e:
        print(f'[WARN] Cannot read prediction {path}: {e}')
        return pd.DataFrame()
    if yt is None:
        print('[WARN] NPZ has no y_true; not guessing from test.csv:', path, keys)
        return pd.DataFrame()
    yt=np.asarray(yt).ravel()
    n=len(yt)
    if probs is None and logits is not None:
        a=np.asarray(logits)
        if a.ndim==2 and a.shape==(n,8):
            a=a-a.max(axis=1,keepdims=True)
            ex=np.exp(a);probs=ex/np.maximum(ex.sum(axis=1,keepdims=True),1e-15)
    if probs is not None:
        probs=np.asarray(probs)
        if probs.shape==(8,n):probs=probs.T
        if probs.shape!=(n,8):probs=None
        elif not (np.isfinite(probs).all() and np.allclose(probs.sum(axis=1),1,atol=2e-2)):
            print('[WARN] Invalid probability matrix, ignoring:',path)
            probs=None
    if yp is None and probs is not None:yp=probs.argmax(axis=1)
    if yp is None:
        print('[WARN] NPZ has no predictions/probabilities:',path,keys)
        return pd.DataFrame()
    yp=np.asarray(yp).ravel()
    if len(yp)!=n:return pd.DataFrame()
    out=pd.DataFrame({'method':method,'seed':seed,'split':'test',
                      'y_true':[canonical_age(x) for x in yt],
                      'y_pred':[canonical_age(x) for x in yp]})
    if ids is not None and len(np.asarray(ids).ravel())==n:
        out['image_id']=np.asarray(ids).ravel().astype(str)
    else:
        out['image_id']=None   # Never pretend an index is an original image filename
    if cache_idxs is not None and len(np.asarray(cache_idxs).ravel()) == n:
        out['cache_index']=np.asarray(cache_idxs).ravel()
    else:
        out['cache_index']=None
    out['confidence']=probs.max(axis=1) if probs is not None else np.nan
    if probs is not None:
        for j in range(8):out[f'prob_{j}']=probs[:,j]
    return out


def _safe_cache_key(value):
    """Match explicit cache indices, not row order (avoids silent label errors)."""
    if pd.isna(value):
        return None
    value=str(value).strip()
    if not value:
        return None
    try:
        z=float(value)
        if np.isfinite(z) and z.is_integer():
            return str(int(z))
    except ValueError:
        pass
    return value


def attach_real_image_ids(df, npz_path, cache):
    """Use documented cache_index joins to find image names for Hinh 18.

    An index into a tensor is NOT assumed to equal a row number in test.csv.
    We only join on an explicitly named cache_index in both sources, and
    validate age-group labels when the metadata supplies them.
    """
    if 'cache_index' not in df or df.cache_index.isna().all():
        return df
    branch=Path(npz_path).parents[2]
    key=str(branch)
    if key not in cache:
        table=[]
        for source_label in ['test.csv','manifest.csv']:
            source=branch/'data'/source_label
            if not source.is_file():
                continue
            try:
                raw=read_table(source)
            except Exception as exc:
                print('[WARN] Cannot read image mapping:',source,exc)
                continue
            idx=find_col(raw,['cache_index','cache_idx'])
            img=find_col(raw,['image_id','image_path','relative_path','filepath','file_path',
                              'filename','file_name','path','image','image_name','img_path',
                              'original_filename','original_path','source_path','source_file','name'])
            lab=find_col(raw,['age_group','age_bin','group','label','y','age_label','target'])
            if idx is None or img is None:
                continue
            mapping={}
            conflicts=set()
            for _,r in raw.iterrows():
                k=_safe_cache_key(r[idx]); image_value=r[img]
                if k is None or pd.isna(image_value) or not str(image_value).strip():
                    continue
                v=(str(image_value).strip(),canonical_age(r[lab]) if lab is not None else None)
                if k in mapping and mapping[k]!=v:
                    conflicts.add(k)
                else:
                    mapping[k]=v
            for k in conflicts:
                mapping.pop(k,None)
            if mapping:
                table.append((source_label,mapping))
        cache[key]=table
    if not cache[key]:
        return df
    out=df.copy()
    missing=out.image_id.isna()
    for source_name,mapping in cache[key]:
        if not missing.any():break
        keys=out.loc[missing,'cache_index'].map(_safe_cache_key)
        matches=keys.map(mapping)
        m_idx=out.index[missing]
        filled=0
        rejected=0
        for i,match in zip(m_idx,matches):
            if not isinstance(match,tuple):continue
            img,lab=match
            if lab is not None and lab!=out.at[i,'y_true']:
                rejected+=1
                continue
            out.at[i,'image_id']=img
            filled+=1
        if filled:
            print(f'[INFO] Matched {filled}/{len(out)} image IDs using {source_name} and cache_index: {npz_path.parent.name}')
        if rejected:
            print(f'[WARN] Rejected {rejected} IDs because true label mismatched metadata: {source_name}')
        missing=out.image_id.isna()
    return out

class Context:
    def __init__(self, root, out, paths, data, nosqrt, images=None):
        self.root, self.out, self.paths = root, out, paths
        self.d, self.no = data, nosqrt
        self.images = Path(images) if images else None
        self.success = []
        self.skipped = []
        self.cache = {}

    def table(self, names, prefer=None):
        key = (tuple(names), prefer)
        if key in self.cache:
            return self.cache[key]
        p = get_path(self.paths, names, prefer)
        if p is None:
            return None
        try:
            v = read_table(p)
            self.cache[key] = v
            return v
        except Exception as exc:
            print('[WARN] Loi doc file:', p, exc)
            return None

    def table_paths(self, pattern):
        return [p for p in self.paths if re.search(pattern, p.name, re.I)]

    def combined(self):
        if self.no.empty:
            return self.d.copy()
        no = self.no.copy()
        no['method'] = 'NoSqrt'
        return pd.concat([self.d, no], ignore_index=True)

    def ensure(self, cols, df=None):
        d = self.d if df is None else df
        miss = [c for c in cols if c not in d.columns]
        if miss:
            raise ValueError('Thieu cot: ' + ', '.join(miss))
        if d.empty:
            raise ValueError('Khong co du lieu run/seed')


def fig01(c):
    c.ensure(['qwk', 'f1_macro'])
    d = c.d[c.d.split == 'test']
    order = summary(d, 'qwk').sort_values(['mean', 'method'], ascending=[False, True]).method.tolist()
    fail_if(len(order) < 2, 'Thieu cac cau hinh test de xep hang')
    fig, axes = plt.subplots(1, 2, figsize=(13, max(6, .38*len(order)+1)), sharey=True)
    for ax, metric, caption in zip(axes, ['qwk', 'f1_macro'], ['QWK (higher is better)', 'Macro F1 (higher is better)']):
        for j, m in enumerate(order):
            v = d.loc[d.method == m, metric].dropna().to_numpy()
            if not len(v): continue
            sd = np.std(v, ddof=1) if len(v)>1 else 0
            ax.scatter(v, np.full(len(v), j)+np.linspace(-.12,.12,len(v)), alpha=.44, s=17, c=COLORS.get(m,'#4f7ca4'))
            ax.errorbar(v.mean(), j, xerr=sd, fmt='o', capsize=3, color='#192936', markersize=4)
        ax.set_xlabel(caption)
        ax.grid(axis='x', color='#e6e8eb')
    axes[0].invert_yaxis()
    axes[0].set_yticks(range(len(order)), order)
    axes[0].set_title('Sorted by mean QWK (test)')
    axes[1].set_title('Same order: Macro F1 (test)')
    fig.suptitle('Overall comparison: 3 seeds and mean ± sample SD', fontsize=13)
    save(fig,c,1,'QWK and Macro F1 of all methods')


def fig04(c):
    c.ensure(['qwk','nll'])
    d=c.d[c.d.split=='test'].groupby('method',as_index=False)[['qwk','nll']].mean().dropna()
    fail_if(len(d)<2,'Khong du 2 cau hinh')
    fig,ax=plt.subplots(figsize=(9,6))
    ax.scatter(d.nll,d.qwk,color='#a3b0ba',s=45,alpha=.8)
    for _,r in d.iterrows():
        m=r.method
        if m in {'A1','A2','A12','A4_5'}:
            ax.scatter(r.nll,r.qwk,c=COLORS.get(m,'#405c74'),s=100,edgecolors='white',zorder=4)
            ax.annotate(m,(r.nll,r.qwk),xytext=(6,6),textcoords='offset points',fontsize=10,weight='bold')
        else:
            ax.annotate(m,(r.nll,r.qwk),xytext=(3,3),textcoords='offset points',fontsize=8,color='#5a6670')
    ax.set(xlabel='NLL ↓', ylabel='QWK ↑',title='QWK vs NLL — Test mean across seeds')
    style_axis(ax); save(fig,c,4,'QWK–NLL tradeoff')


def fig05(c):
    c.ensure(['qwk','group_mae','f1_macro','nll'])
    methods=['A1','A2','A3','A12']
    fig,axs=plt.subplots(2,2,figsize=(11,8))
    for ax,metric,ttl in zip(axs.flat,['qwk','group_mae','f1_macro','nll'],['QWK ↑','MAE ↓','Macro F1 ↑','NLL ↓']):
        for seed in sorted(c.d.seed.unique()):
            y=[val(c.d,m,seed,metric) for m in methods]
            if np.isfinite(y).any(): ax.plot(methods,y,marker='o',lw=1.6,label=f'Seed {seed}')
        ax.set_title(ttl);style_axis(ax)
    axs.flat[0].legend(loc='best',fontsize=8)
    fig.suptitle('A1 → A2 → A3 → A12 (paired by seed)',size=13)
    fig.tight_layout();save(fig,c,5,'C / O / weighted O / combined')


def fig06(c):
    c.ensure(['qwk'])
    fail_if(not (c.d.split=='val').any(),'Khong co split=val, khong the so sanh validation va test')
    fig,ax=plt.subplots(figsize=(9,6))
    ms=list(LAMBDA)
    for split,clr in [('val','#396ba3'),('test','#bc7832')]:
        s=summary(c.d,'qwk',ms,split).set_index('method')
        x=[]; y=[]; e=[]
        for m in ms:
            if m in s.index:
                x.append(LAMBDA[m]);y.append(s.loc[m,'mean']);e.append(s.loc[m,'sd'])
        if x: ax.errorbar(x,y,yerr=np.nan_to_num(e),marker='o',label=split.upper(),capsize=3,color=clr)
    ref=summary(c.d,'qwk',['A12'])
    if len(ref): ax.axhline(ref['mean'].iloc[0],ls='--',color=COLORS['A12'],label='A12 test mean')
    ax.axvline(.5,ls=':',color='gray',label='lambda=0.5')
    ax.set_xscale('log');ax.set_xticks(list(LAMBDA.values()), [str(x) for x in LAMBDA.values()])
    ax.set(xlabel='Fixed lambda (log scale)',ylabel='QWK ↑',title='Validation vs test QWK for fixed lambda')
    ax.legend();style_axis(ax);save(fig,c,6,'Validation/test QWK by lambda')


def fig07(c):
    c.ensure(['group_mae','f1_macro','nll'])
    fig,axs=plt.subplots(1,3,figsize=(14,4.8))
    for ax,metric,lab in zip(axs,['group_mae','f1_macro','nll'],['MAE ↓','Macro F1 ↑','NLL ↓']):
        s=summary(c.d,metric,LAMBDA).set_index('method')
        items=[(LAMBDA[m],s.loc[m,'mean'],s.loc[m,'sd']) for m in LAMBDA if m in s.index]
        if not items: continue
        x,y,e=map(np.array,zip(*items))
        ax.errorbar(x,y,yerr=np.nan_to_num(e),capsize=3,marker='o',color='#396ba3')
        ax.set_xscale('log');ax.set_xticks(list(LAMBDA.values()), [str(x) for x in LAMBDA.values()]);ax.set_xlabel('Fixed lambda');ax.set_title(lab);style_axis(ax)
    fig.suptitle('Sensitivity to fixed ordinal weight',fontsize=13)
    fig.tight_layout();save(fig,c,7,'MAE, Macro F1 and NLL sensitivity to lambda')


def fig08(c):
    c.ensure(['qwk','nll'])
    methods=sorted([m for m in ABLS if len(paired(c.d,m,metric='qwk'))],
                   key=lambda m:-nansafe_mean(paired(c.d,m,metric='qwk')))
    fail_if(not methods,'Khong co cap seed chung voi A12')
    fig,axs=plt.subplots(1,2,figsize=(12,max(5,.45*len(methods)+1)),sharey=True)
    for ax,metric,higher,ttl in zip(axs,['qwk','nll'],[True,False],['Δ QWK: A12 − baseline','NLL reduction: baseline − A12']):
        for j,m in enumerate(methods):
            v=paired(c.d,m,metric=metric,higher=higher)
            if len(v):
                ax.scatter(v,np.full(len(v),j)+np.linspace(-.10,.10,len(v)),s=26,c='#98b4ca',alpha=.85)
                ax.scatter(v.mean(),j,s=40,c=COLORS['A12'],marker='D',zorder=3)
        ax.axvline(0,color='#20282e',lw=1);ax.set(xlabel=ttl)
        ax.grid(axis='x',alpha=.2)
    axs[0].set_yticks(range(len(methods)),methods);axs[0].invert_yaxis()
    fig.suptitle('Paired ablation deltas on the same seed',size=13)
    save(fig,c,8,'Paired QWK and NLL ablation deltas')


def fig09(c):
    c.ensure(['qwk','group_mae','f1_macro','ece15','nll'])
    metrics=['qwk','group_mae','f1_macro','ece15','nll']
    methods=sorted([m for m in ABLS if len(paired(c.d,m,metric='qwk'))],
                   key=lambda m:-nansafe_mean(paired(c.d,m,metric='qwk')))
    fail_if(not methods,'Khong co seed chung')
    mat=np.full((len(methods),len(metrics)),np.nan)
    denominators=np.zeros((len(methods),len(metrics)),dtype=int)
    for j,m in enumerate(methods):
        for k,metric in enumerate(metrics):
            x=paired(c.d,m,metric=metric,higher=(metric not in LOWER))
            if len(x):
                mat[j,k]=(x>0).sum()
                denominators[j,k]=len(x)
    fig,ax=plt.subplots(figsize=(9,max(5,len(methods)*.45+1)))
    im=ax.imshow(np.ma.masked_invalid(mat),cmap='Blues',vmin=0,vmax=3,aspect='auto')
    ax.set_xticks(range(len(metrics)),['QWK','MAE','F1','ECE15','NLL']);ax.set_yticks(range(len(methods)),methods)
    for (j,k),v in np.ndenumerate(mat):
        if np.isfinite(v):
            ax.text(k,j,f'{int(v)}/{denominators[j,k]}',ha='center',va='center',
                    color='white' if v>=2 else '#18384e',fontsize=9)
    fig.colorbar(im,ax=ax,label='Number of winning seeds')
    ax.set_title('A12 wins vs ablations — paired seeds (ties not counted)')
    save(fig,c,9,'Winning-seed heatmap across metrics')


def fig10(c):
    multi_comparison(c,10,['A5','A7','A12'],['qwk','group_mae','f1_macro','nll'],
                     'Effects of different ordinal weighting')


def fig11(c):
    multi_comparison(c,11,['A6','A10','A12'],['qwk','f1_macro','ece15','nll'],
                     'Class weights in C and O')


def fig12(c):
    multi_comparison(c,12,['A8','A9','A11','A12'],['qwk','accuracy','ece15','nll'],
                     'Focal term, stop-gradient, and lambda focal')


def multi_comparison(c,index,methods,metrics,title):
    c.ensure(metrics)
    fig,axs=plt.subplots(2,2,figsize=(11,8))
    for ax,metric in zip(axs.flat,metrics):
        plot_dot(ax,c.d,metric,methods,metric + (' ↓' if metric in LOWER else ' ↑'))
    fig.suptitle(title,fontsize=13);fig.tight_layout()
    save(fig,c,index,title)


def fig13(c):
    d=c.combined()
    c.ensure(['qwk','accuracy','nll','ece15'],d)
    fail_if(c.no.empty,'Khong co test_by_seed.csv NoSqrt')
    fig,axs=plt.subplots(2,2,figsize=(10,8))
    for ax,metric in zip(axs.flat,['qwk','accuracy','nll','ece15']):
        common=sorted(set(d.loc[d.method=='A12','seed']) & set(d.loc[d.method=='NoSqrt','seed']))
        for seed in common:
            y=[val(d,'A12',seed,metric),val(d,'NoSqrt',seed,metric)]
            if np.all(np.isfinite(y)):
                ax.plot([0,1],y,'-o',label=f'Seed {seed}',alpha=.86)
        ax.set_xticks([0,1],['A12-Sqrt','A12-NoSqrt']);ax.set_title(metric + (' ↓' if metric in LOWER else ' ↑'))
        style_axis(ax)
    axs.flat[0].legend(fontsize=8)
    fig.suptitle('Sqrt vs NoSqrt: per-seed comparison',fontsize=13);fig.tight_layout()
    save(fig,c,13,'Sqrt–NoSqrt paired by seed')


def fig14(c):
    d=c.combined()
    c.ensure(['accuracy','within1','within2'],d)
    ms=['A12','NoSqrt']
    layers=[]
    for m in ms:
        df=d[(d.method==m) & (d.split=='test')]
        if df.empty: raise ValueError('Thieu test cho '+m)
        a,w1,w2=(df[x].mean() for x in ['accuracy','within1','within2'])
        z=np.array([a,w1-a,w2-w1,1-w2])
        if np.any(z<-.005): raise ValueError(f'Within1/Within2 khong nhat quan: {m}: {z}')
        layers.append(np.maximum(z,0))
    layers=np.asarray(layers).T
    fig,ax=plt.subplots(figsize=(9,5))
    bottom=np.zeros(2)
    for k,(label,co) in enumerate(zip(['Correct','Off by 1','Off by 2','Off by ≥3'],['#228B75','#E8B85C','#A477AC','#C85C60'])):
        vals=layers[k]*100
        ax.bar(ms,vals,bottom=bottom,color=co,label=label)
        for j,v in enumerate(vals):
            if v>2: ax.text(j,bottom[j]+v/2,f'{v:.2f}%',ha='center',va='center',fontsize=9)
        bottom+=vals
    ax.set_ylim(0,105);ax.set_ylabel('Percentage of test predictions (%)')
    ax.legend(loc='upper center',ncol=4,bbox_to_anchor=(.5,1.16))
    ax.set_title('Distribution of absolute ordinal errors (mean across seeds)')
    save(fig,c,14,'Ordinal error-distance decomposition')


def load_train_counts(c):
    # In the real tree, class counts are in Sqrt/data/train.csv.
    candidates=[p for p in c.paths if p.name.lower()=='train.csv'
                and '/data/' in p.as_posix().lower()]
    candidates.sort(key=lambda p:(source_variant(p)!='Sqrt',len(str(p))))
    for p in candidates:
        try:
            raw=read_table(p)
            cls=find_col(raw,['age_group','age_bin','age_bucket','age_class',
                              'group','group_label','group_id','label','class_id',
                              'class','target','age_label'])
            if cls:
                counts=raw[cls].dropna().map(canonical_age).value_counts().to_dict()
                if len(set(AGES)&set(counts))==8:return counts
        except Exception:pass
    # If user has precomputed age-group counts, use them.
    p=get_path(c.paths,['train_counts.csv','class_counts_train.csv','train_class_counts.csv',
                        'train_counts.json','class_counts_train.json'])
    if p is None:return None
    if p.suffix=='.json':
        obj=read_json_small(p)
        return {canonical_age(k):int(v) for k,v in obj.items()} if isinstance(obj,dict) else None
    df=read_table(p)
    cc=find_col(df,['class','class_id','age_group','label'])
    nc=find_col(df,['count','n','samples','support'])
    if cc is None or nc is None:return None
    return {canonical_age(k):int(v) for k,v in zip(df[cc],df[nc]) if num(v)>0}

def canonical_age(raw):
    s=str(raw).strip().replace('–','-').replace(' ','').replace('_','-')
    if s in ('7','70','70+','>=70','70plus'):return '70+'
    if s.endswith('.0') and s[:-2].isdigit():s=s[:-2]
    if s.isdigit() and int(s) in range(8):return AGES[int(s)]
    return s


def fig15(c):
    d=c.combined()
    c.ensure(['accuracy'],d)
    cnt=load_train_counts(c)
    fail_if(not cnt,'Thieu train_counts.csv (class/count) de tinh trong so tren TAP TRAIN')
    cnt={canonical_age(k):v for k,v in cnt.items()}
    fail_if(any(k not in cnt for k in AGES),'train_counts.csv can du 8 nhom tuoi: '+', '.join(AGES))
    ns=np.array([cnt[k] for k in AGES],dtype=float)
    beta=.999
    raw=(1-beta)/(1-np.power(beta,ns))
    weights=[]
    for power in [.5,1.0]:
        v=raw**power
        weights.append(v/v.sum()*len(v))
    fig,axs=plt.subplots(1,2,figsize=(14,5))
    x=np.arange(8)
    axs[0].plot(x,weights[0],'-o',label='Sqrt: exponent 0.5',color=COLORS['A12'])
    axs[0].plot(x,weights[1],'-o',label='NoSqrt: exponent 1',color=COLORS['NoSqrt'])
    axs[0].set_xticks(x,AGES,rotation=40);axs[0].set_ylabel('Normalized class weight')
    axs[0].set_title('Train class weights, beta=0.999');axs[0].legend();style_axis(axs[0])
    for m,co in [('A12',COLORS['A12']),('NoSqrt',COLORS['NoSqrt'])]:
        for seed in sorted(d.loc[d.method==m,'seed'].unique()):
            tr=val(d,m,seed,'accuracy','train'); te=val(d,m,seed,'accuracy','test')
            if np.isfinite(tr) and np.isfinite(te):
                axs[1].plot([0,1],[tr,te],'-o',color=co,alpha=.5)
        a=[val(d,m,s,'accuracy','train') for s in sorted(d.seed.unique())]
        b=[val(d,m,s,'accuracy','test') for s in sorted(d.seed.unique())]
        if np.isfinite(a).any() and np.isfinite(b).any():
            axs[1].plot([0,1],[nansafe_mean(a),nansafe_mean(b)],'-D',lw=2.4,color=co,label=m)
    axs[1].set_xticks([0,1],['Train','Test']);axs[1].set_title('Accuracy at selected checkpoint');axs[1].legend();style_axis(axs[1])
    fail_if(not (d.split=='train').any(),'Khong co thong tin train Accuracy theo seed')
    fig.tight_layout();save(fig,c,15,'Class-weight scale vs train/test gap')


def normalize_perclass(df, default_method=None):
    mc=find_col(df,['method','experiment','variant','model','run_name'])
    sc=find_col(df,['seed','random_seed'])
    cl=find_col(df,['class','class_id','class_name','age_group','label','grade'])
    if cl is None:return pd.DataFrame()
    f=find_col(df,['f1','f1_score','f1score','f1_mean','f1_macro'])
    sup=find_col(df,['support','count','n','num_samples'])
    if f is None:return pd.DataFrame()
    out=pd.DataFrame({'method':df[mc].map(method_name) if mc else default_method,
                      'class':df[cl].map(canonical_age),
                      'f1':pd.to_numeric(df[f],errors='coerce')})
    out['seed']=pd.to_numeric(df[sc],errors='coerce') if sc else np.nan
    out['support']=pd.to_numeric(df[sup],errors='coerce') if sup else np.nan
    return out


def get_perclass(c):
    frames=[]
    for p in c.table_paths(r'per[_-]?class.*\.(csv|xlsx)$'):
        try:
            n=normalize_perclass(read_table(p),
                'NoSqrt' if source_variant(p)=='NoSqrt' else None)
            if not n.empty:frames.append(n)
        except Exception as e:print('[WARN] Per-class:',p,e)
    preds=get_preds(c)
    if not preds.empty:
        records=[]
        for (model,seed), df in preds.groupby(['method','seed']):
            gt=df.y_true.to_numpy();pr=df.y_pred.to_numpy()
            if not set(gt).issubset(AGES) or not set(pr).issubset(AGES):continue
            for age in AGES:
                tp=((gt==age)&(pr==age)).sum()
                n_true=(gt==age).sum(); n_pred=(pr==age).sum()
                prec=tp/n_pred if n_pred else 0.
                rec=tp/n_true if n_true else 0.
                f1=2*prec*rec/(prec+rec) if prec+rec else 0.
                records.append({'method':model,'seed':seed,'class':age,'f1':f1,
                                'support':n_true})
        if records:
            from_preds=pd.DataFrame(records)
            if frames:
                all_df=pd.concat(frames,ignore_index=True)
                # Replace per-class summary for any model+seed covered by raw NPZ
                if 'seed' in all_df and all_df['seed'].notna().any():
                    idx=set(zip(from_preds.method,from_preds.seed))
                    all_df=all_df[[ (m,s) not in idx for m,s in zip(all_df.method,all_df.seed) ]]
                    from_preds=pd.concat([all_df,from_preds],ignore_index=True)
                frames=[from_preds]
            else:frames=[from_preds]
    if not frames:return pd.DataFrame()
    d=pd.concat(frames,ignore_index=True)
    d['class']=d['class'].map(canonical_age)
    return d.dropna(subset=['method','f1'])

def fig16(c):
    d=get_perclass(c)
    fail_if(d.empty,'Thieu per_class.csv cua cac mo hinh (class,f1,support[,seed,method])')
    d=d[d.method.isin(['A2','A12','NoSqrt'])].copy()
    fail_if(d.empty,'Per-class khong co A2, A12 hoac NoSqrt')
    s=d.groupby(['method','class'],as_index=False).agg(f1=('f1','mean'),sd=('f1','std'),support=('support','mean'))
    ref=s[s.method=='NoSqrt']
    if ref.empty:ref=s[s.method=='A12']
    order=ref.sort_values('f1')['class'].tolist()
    for a in AGES:
        if a not in order:order.append(a)
    fig,ax=plt.subplots(figsize=(12,6))
    methods=[m for m in ['A2','A12','NoSqrt'] if m in set(s.method)]
    width=.78/len(methods);x=np.arange(len(order))
    for j,m in enumerate(methods):
        vals=[]; err=[]
        for a in order:
            z=s[(s.method==m)&(s['class']==a)]
            vals.append(float(z.f1.iloc[0]) if len(z) else np.nan)
            err.append(float(z.sd.iloc[0]) if len(z) else np.nan)
        ax.bar(x-.39+width*(j+.5),vals,width,yerr=np.nan_to_num(err),capsize=2,
               label=m,color=COLORS.get(m,'#74889b'),alpha=.8)
    # Support cua tung nhom tuoi duoc ghi ngay tren nhan truc x.
    supports={}
    for a in order:
        z=s[s['class']==a]['support'].dropna()
        supports[a]=int(round(z.mean())) if len(z) else None
    labels=[f"{a}\nn={supports[a]}" if supports[a] is not None else a for a in order]
    ax.set_xticks(x,labels,rotation=25);ax.set_ylabel('F1 per age group ↑')
    ax.set_title('Per-class F1 (order: NoSqrt / A12 ascending)')
    ax.legend();style_axis(ax)
    save(fig,c,16,'F1 by age class with sample support source')


def normalize_preds(df,default_method=None):
    mc=find_col(df,['method','experiment','variant','model','run_name'])
    sc=find_col(df,['seed','random_seed'])
    yc=find_col(df,['y_true','true_label','target','label','ground_truth','gt'])
    pc=find_col(df,['y_pred','predicted','prediction','pred_label','pred_class','pred'])
    if yc is None or pc is None:return pd.DataFrame()
    idc=find_col(df,['image_id','image','id','filename','file','path','image_path','filepath'])
    cc=find_col(df,['confidence','conf','max_prob','pred_confidence','prob_max'])
    spl=find_col(df,['split','phase','dataset'])
    out=pd.DataFrame({'method':df[mc].map(method_name) if mc else default_method,
                      'seed':pd.to_numeric(df[sc],errors='coerce') if sc else np.nan,
                      'y_true':df[yc].map(canonical_age),
                      'y_pred':df[pc].map(canonical_age),
                      'image_id':df[idc].astype(str) if idc else np.arange(len(df)).astype(str),
                      'split':df[spl].astype(str).str.lower() if spl else 'test'})
    out['confidence']=pd.to_numeric(df[cc],errors='coerce') if cc else np.nan
    for col in df.columns:
        match=re.fullmatch(r'(?:p|prob|probability|proba)[_-]?(\d+)',name_key(col))
        if match and int(match.group(1)) in range(8):
            out['prob_'+match.group(1)]=pd.to_numeric(df[col],errors='coerce')
    c_probs=find_col(df,['probabilities','probs','softmax','y_prob'])
    if c_probs:
        def as_arr(s):
            if isinstance(s,(list,tuple,np.ndarray)):return s
            try:return json.loads(str(s))
            except Exception:
                try:return ast.literal_eval(str(s))
                except Exception:return []
        arr=df[c_probs].map(as_arr)
        for j in range(8):
            out['prob_'+str(j)]=arr.map(lambda x: x[j] if len(x)>j else np.nan)
    prob_cols=['prob_'+str(j) for j in range(8)]
    if all(x in out for x in prob_cols) and out['confidence'].isna().all():
        out['confidence']=out[prob_cols].max(axis=1)
    return out


def get_preds(c):
    if 'preds' in c.cache:return c.cache['preds']
    arr=[]
    # The supplied folder structure stores predictions in *.npz, not *.csv.
    for p in c.paths:
        if p.name!='test_predictions.npz':continue
        method, seed=run_identity(p)
        if method not in {'A1','A2','A12','NoSqrt'}:continue
        df=read_npz_pred(p)
        if not df.empty:
            if method=='NoSqrt' and df.image_id.isna().any():
                df=attach_real_image_ids(df,p,c.cache.setdefault('image_maps',{}))
            arr.append(df)
    # CSV predictions are supported when available.
    for p in c.table_paths(r'predictions?.*\.(csv|xlsx|parquet)$'):
        try:
            raw=pd.read_parquet(p) if p.suffix=='.parquet' else read_table(p)
            default='NoSqrt' if source_variant(p)=='NoSqrt' else None
            n=normalize_preds(raw,default)
            if not n.empty:arr.append(n)
        except Exception as exc:print('[WARN] Prediction table:',p,exc)
    if arr:
        preds=pd.concat(arr,ignore_index=True)
        # Prefer NPZ when both CSV and NPZ exist (first record).
        c.cache['preds']=preds.drop_duplicates(['method','seed','image_id'],keep='first') if preds.image_id.notna().all() else preds
    else:c.cache['preds']=pd.DataFrame()
    return c.cache['preds']

def get_bins(c):
    arr=[]
    for p in c.table_paths(r'(calibration|reliability|bins_15).*\.(csv|xlsx)$'):
        try:
            df=read_table(p)
            mc=find_col(df,['method','experiment','variant','model'])
            sc=find_col(df,['seed'])
            acc=find_col(df,['accuracy','acc','avg_accuracy','mean_accuracy','bin_accuracy'])
            conf=find_col(df,['confidence','avg_confidence','mean_confidence','bin_confidence'])
            count=find_col(df,['count','n','num_samples','bin_count','samples'])
            bn=find_col(df,['bin','bin_id','bin_index','bin_center','bin_lower','bin_start'])
            if not all([acc,conf,count]):continue
            default='NoSqrt' if 'nosqrt' in str(p).lower() else ('A12' if 'a12' in str(p).lower() else None)
            x=pd.DataFrame({'method':df[mc].map(method_name) if mc else default,
                            'seed':pd.to_numeric(df[sc],errors='coerce') if sc else 0,
                            'accuracy':pd.to_numeric(df[acc],errors='coerce'),
                            'confidence':pd.to_numeric(df[conf],errors='coerce'),
                            'count':pd.to_numeric(df[count],errors='coerce'),
                            'bin':df[bn] if bn else np.floor(pd.to_numeric(df[conf],errors='coerce')*15).clip(0,14).astype('Int64')})
            arr.append(x)
        except Exception:pass
    return pd.concat(arr,ignore_index=True) if arr else pd.DataFrame()


def confidence_bins(preds, bins=15):
    if preds.empty or 'confidence' not in preds:return pd.DataFrame()
    records=[]
    for (m,s),g in preds.dropna(subset=['confidence']).groupby(['method','seed'],dropna=False):
        gt=g.y_true.to_numpy();pr=g.y_pred.to_numpy(); conf=g.confidence.to_numpy(float)
        valid=np.isfinite(conf)&(conf>=0)&(conf<=1)
        idx=np.minimum(np.floor(conf[valid]*bins).astype(int),bins-1)
        for b in range(bins):
            mask=idx==b
            if mask.any():
                records.append({'method':m,'seed':s,'bin':b,'accuracy':float((gt[valid][mask]==pr[valid][mask]).mean()),
                                'confidence':float(conf[valid][mask].mean()),'count':int(mask.sum())})
    return pd.DataFrame(records)


def fig02(c):
    bins=get_bins(c)
    if bins.empty:bins=confidence_bins(get_preds(c))
    fail_if(bins.empty,'Can calibration_bins_15.csv hoac predictions co confidence')
    # Aggregate via so luong, khong lay mean don gian cua bin tren cac seed
    fig,axs=plt.subplots(2,2,figsize=(11,9))
    for ax,m in zip(axs.flat,['A1','A2','A12','NoSqrt']):
        x=bins[bins.method==m].dropna(subset=['count','confidence','accuracy']).copy()
        if x.empty:
            ax.text(.5,.5,f'No data for {m}',ha='center',va='center',transform=ax.transAxes)
            ax.set_xlim(0,1);ax.set_ylim(0,1);ax.set_title(m);continue
        # Can chuan hoa bin: tu confidence hoac index neu ten bin khong tuong thich
        x['bin_index']=np.floor(x.confidence.clip(0,.999999)*15).astype(int)
        s=x.assign(wconf=x.confidence*x['count'],wacc=x.accuracy*x['count']).groupby('bin_index').agg(
            cnt=('count','sum'),co=('wconf','sum'),ac=('wacc','sum'))
        conf=s.co/s.cnt; acc=s.ac/s.cnt
        ax.plot([0,1],[0,1],ls='--',color='#8a949d',label='Ideal')
        ax.plot(conf,acc,'-o',color=COLORS.get(m,'#446c99'),label='Observed')
        for xx,yy,n in zip(conf,acc,s.cnt):
            ax.annotate(str(int(n)),(xx,yy),xytext=(2,4),textcoords='offset points',fontsize=7,color='#6d7580')
        ax.set(xlim=(0,1),ylim=(0,1),title=m,xlabel='Mean confidence',ylabel='Accuracy')
        ax.legend(fontsize=8);style_axis(ax)
    fig.suptitle('Reliability diagrams: 15 bins (numbers = prediction counts)',size=13)
    fig.tight_layout();save(fig,c,2,'Reliability diagrams by model')


def fig03(c):
    df=get_preds(c)
    fail_if(df.empty,'Can predictions.csv chi tiet')
    fail_if('confidence' not in df or df.confidence.notna().sum()==0,'Can confidence/probabilities tung anh')
    fig,axs=plt.subplots(2,2,figsize=(11,8))
    plotted=0
    for ax,m in zip(axs.flat,['A1','A2','A12','NoSqrt']):
        x=df[(df.method==m)&(df.split=='test')].dropna(subset=['confidence'])
        if x.empty:ax.set_title(f'{m} (missing)');continue
        # Equal per-seed contribution; pooled predictions count as repeated evaluations
        correct=x[x.y_true==x.y_pred].confidence
        wrong=x[x.y_true!=x.y_pred].confidence
        for values,clr,label in [(correct,'#3a9e86','Correct'),(wrong,'#c87856','Incorrect')]:
            if len(values):
                ax.hist(values,bins=np.linspace(0,1,21),alpha=.65,density=True,
                        label=f'{label} (n={len(values)})',color=clr)
        ax.set(xlim=(0,1),title=f'{m}: {len(x)} predictions',xlabel='Predicted-class confidence',ylabel='Density')
        ax.legend(fontsize=8);style_axis(ax);plotted+=1
    fail_if(plotted==0,'Khong co predictions test cho A1/A2/A12/NoSqrt')
    fig.suptitle('Correct vs incorrect confidence (consistent bins)',size=13);fig.tight_layout()
    save(fig,c,3,'Correct/incorrect confidence distributions')


def get_cm(c):
    p=get_preds(c)
    if not p.empty:
        x=p[(p.method=='NoSqrt')&(p.split=='test')].dropna(subset=['y_true','y_pred'])
        if not x.empty:
            mat=np.zeros((8,8),dtype=np.int64)
            for a,b in zip(x.y_true,x.y_pred):
                if a in AGES and b in AGES:mat[AGES.index(a),AGES.index(b)]+=1
            if mat.sum():return mat
    # Co the co matrix 8x8 xuat truc tiep
    for f in c.table_paths(r'confusion[_-]?matrix.*\.csv$'):
        if 'nosqrt' not in str(f).lower() and 'no_sqrt' not in str(f).lower():continue
        try:
            x=pd.read_csv(f,header=None)
            x=x.apply(pd.to_numeric,errors='coerce').dropna(axis=0,how='all').dropna(axis=1,how='all')
            if x.shape==(8,8):return x.to_numpy(dtype=int)
        except Exception:pass
    return None


def fig17(c):
    mat=get_cm(c)
    fail_if(mat is None,'Can confusion_matrix NoSqrt hoac predictions NoSqrt cua ba seed')
    norm=mat/np.maximum(mat.sum(axis=1,keepdims=True),1)
    fig,ax=plt.subplots(figsize=(10,8))
    im=ax.imshow(norm,cmap='Blues',vmin=0,vmax=1)
    ax.set_xticks(range(8),AGES,rotation=45);ax.set_yticks(range(8),AGES)
    for i in range(8):
        for j in range(8):
            v=norm[i,j]
            ax.text(j,i,f'{100*v:.1f}%',ha='center',va='center',fontsize=8,color='white' if v>.52 else '#173047')
    fig.colorbar(im,ax=ax,label='Within-true-class percentage')
    ax.set(xlabel='Predicted age group',ylabel='True age group',
           title=f'NoSqrt normalized confusion matrix — {mat.sum():,} predictions')
    save(fig,c,17,'Normalized NoSqrt confusion matrix')


def resolve_image(image_root,ident,lookup):
    p=Path(str(ident))
    if p.is_file():return p
    if image_root is None:return None
    try:
        full=image_root/p
        if full.is_file():return full
    except OSError:return None
    return lookup.get(p.name) or lookup.get(p.stem)


def fig18(c):
    p=get_preds(c)
    fail_if(p.empty,'Can predictions cho image_id/path, y_true, y_pred, confidence')
    fail_if(c.images is None or not c.images.exists(),'Can --images DUONG_DAN_ANH_UTKFACE')
    x=p[(p.method=='NoSqrt')&(p.split=='test')].dropna(subset=['confidence']).copy()
    fail_if(x.empty,'Can predictions NoSqrt chi tiet')
    x=x.dropna(subset=['image_id'])
    fail_if(x.empty,'NPZ chi co cache_index; can data/test.csv hoac manifest.csv chua cung cache_index va ten anh')
    try:
        from PIL import Image, ImageOps
    except ImportError:
        raise ValueError('Thieu Pillow: python -m pip install pillow')
    x['dist']=x.apply(lambda r:abs(AGES.index(r.y_true)-AGES.index(r.y_pred)) if
                      r.y_true in AGES and r.y_pred in AGES else np.nan,axis=1)
    x=x.dropna(subset=['dist'])
    # Chon quy tac co dinh: confidence cao nhat, tie -> image_id nho nhat.
    # Moi nhom sai lech 3 anh, uu tien moi image_id khac nhau.
    far=x[x.dist.between(4,6)]
    far_label='Off by 4–6'
    if far.empty:
        far=x[x.dist>=3]
        far_label='Most severe available (≥3)'
    sets=[('Correct',x[x.dist==0]),('Off by 1',x[x.dist==1]),(far_label,far)]
    picks=[]
    for cat,data in sets:
        data=data.sort_values(['confidence','image_id'],ascending=[False,True]).drop_duplicates('image_id')
        picks.extend((cat,r) for _,r in data.head(3).iterrows())
    fail_if(not picks,'Khong du anh predictions')
    lookup={}
    for base,dirs,files in os.walk(c.images):
        for f in files:
            if Path(f).suffix.lower() in {'.jpg','.jpeg','.png','.webp','.bmp'}:
                lookup.setdefault(f,str(Path(base)/f));lookup.setdefault(Path(f).stem,str(Path(base)/f))
    fig,axs=plt.subplots(3,3,figsize=(12,12))
    got=0
    for ax in axs.flat:ax.axis('off')
    for k,(cat,r) in enumerate(picks):
        f=resolve_image(c.images,r.image_id,lookup)
        if not f:continue
        try:
            with Image.open(f) as im:
                im=ImageOps.exif_transpose(im).convert('RGB')
                axs.flat[k].imshow(im)
            axs.flat[k].set_title(f'{cat} | true={r.y_true}, pred={r.y_pred}\nconf={r.confidence:.3f}, seed={r.seed}',fontsize=9)
            got+=1
        except Exception:continue
    fail_if(got==0,'Khong map duoc image_id sang anh goc trong --images')
    fig.suptitle('Illustrative test predictions: deterministic high-confidence selection',size=12)
    fig.tight_layout();save(fig,c,18,'UTKFace example predictions and errors')


def fig19(c):
    c.ensure(['qwk','ece15','nll'])
    fig,axs=plt.subplots(1,3,figsize=(13,4.8))
    for ax,met in zip(axs,['qwk','ece15','nll']):
        plot_dot(ax,c.d,met,['A1','A2','A12'],met+(' ↓' if met in LOWER else ' ↑'))
    fig.suptitle('Variation across 3 seeds (sample SD)',size=13);fig.tight_layout()
    save(fig,c,19,'Three-seed variation across key metrics')


def normalize_hist(df):
    ep=find_col(df,['epoch','epoch_id','step','epoch_num'])
    if ep is None:return pd.DataFrame()
    sd=find_col(df,['seed','random_seed'])
    method=find_col(df,['method','experiment','model','variant'])
    train=find_col(df,['train_loss','loss_train','training_loss','train_total_loss','loss'])
    valq=find_col(df,['val_qwk','qwk_val','validation_qwk','val_quadratic_weighted_kappa'])
    valn=find_col(df,['val_nll','nll_val','validation_nll'])
    lr=find_col(df,['lr','learning_rate'])
    out=pd.DataFrame({'epoch':pd.to_numeric(df[ep],errors='coerce'),
                      'seed':pd.to_numeric(df[sd],errors='coerce') if sd else np.nan,
                      'method':df[method].map(method_name) if method else 'NoSqrt'})
    for k,col in [('train_loss',train),('val_qwk',valq),('val_nll',valn),('lr',lr)]:
        if col:out[k]=pd.to_numeric(df[col],errors='coerce')
    return out


def get_hist(c):
    records=[]
    files=[p for p in c.paths if p.name.lower()=='history.csv' and 'runs' in p.parts]
    files.sort(key=lambda p:(source_variant(p)!='NoSqrt',str(p)))
    for p in files:
        method,seed=run_identity(p)
        if method not in {'A12','NoSqrt'}:continue
        try:
            d=normalize_hist(read_table(p))
            if d.empty:continue
            d['method']=method
            d['seed']=seed
            records.append(d)
        except Exception as e:print('[WARN] History:',p,e)
    return pd.concat(records,ignore_index=True) if records else pd.DataFrame()

def fig20(c):
    h=get_hist(c)
    fail_if(h.empty,'Can history_full.csv/JSON theo epoch')
    if 'NoSqrt' in h.method.values:h=h[h.method=='NoSqrt']
    columns=['train_loss','val_qwk','val_nll','lr']
    fail_if(not any(s in h for s in columns),'History khong co 4 metric can ve')
    fig,axs=plt.subplots(2,2,figsize=(11,8))
    for ax,met in zip(axs.flat,columns):
        if met not in h:
            ax.text(.5,.5,'Metric not available',ha='center',transform=ax.transAxes)
            ax.set_title(met);continue
        for seed,g in h.groupby('seed',dropna=False):
            g=g.sort_values('epoch')
            ax.plot(g.epoch,g[met],label=f'Seed {seed}',lw=1.6)
            bp=val(c.combined(),'NoSqrt',seed,'best_epoch')
            if not np.isfinite(bp):bp=val(c.d,'A12',seed,'best_epoch') if (h.method=='A12').all() else np.nan
            if np.isfinite(bp):ax.axvline(bp,color='#b0b7be',ls=':',alpha=.4)
        ax.set(xlabel='Epoch',title=met);style_axis(ax)
    axs.flat[0].legend(fontsize=8)
    fig.suptitle('Learning curves and best epochs (dotted lines)',size=13);fig.tight_layout()
    save(fig,c,20,'NoSqrt training/validation curves')


def fig21(c):
    c.ensure(['training_hours','qwk','nll'])
    d=c.d[c.d.split=='test'].dropna(subset=['training_hours'])
    fail_if(d.empty,'Khong co training_hours')
    fig,axs=plt.subplots(1,2,figsize=(13,5))
    for ax,metric in zip(axs,['qwk','nll']):
        for m,g in d.groupby('method'):
            ax.scatter(g.training_hours*60,g[metric],s=30,alpha=.7,
                       color=COLORS.get(m,'#9aa6b1'),label=m if m in ['A2','A12'] else None)
        ax.set(xlabel='Training duration (minutes/run)',ylabel=metric+(' ↓' if metric=='nll' else ' ↑'))
        style_axis(ax)
    axs[0].legend(title='Highlighted',fontsize=8)
    fig.suptitle('Training time vs test quality (all seed-level runs)',size=13);fig.tight_layout()
    save(fig,c,21,'Accuracy/calibration vs training cost')


def run_all(c):
    functions={1:fig01,2:fig02,3:fig03,4:fig04,5:fig05,6:fig06,7:fig07,
               8:fig08,9:fig09,10:fig10,11:fig11,12:fig12,13:fig13,
               14:fig14,15:fig15,16:fig16,17:fig17,18:fig18,19:fig19,
               20:fig20,21:fig21}
    for i,func in functions.items():
        try:
            func(c)
        except Exception as exc:
            plt.close('all')
            reason=str(exc)
            c.skipped.append((i,reason))
            print(f'[SKIP] Hinh_{i:02d}: {reason}')
            if os.environ.get('DEBUG_UTKFACE_FIGURES')=='1':traceback.print_exc()
    with (c.out/'log_tao_hinh.txt').open('w',encoding='utf-8') as f:
        f.write('VE HINH TU BAO CAO UTKFACE - KHONG DUNG DU LIEU GIA\n')
        f.write(f'Root: {c.root}\nNum source paths: {len(c.paths)}\n')
        f.write('\nHINH DA TAO:\n')
        for i,n,title in c.success:f.write(f'Hinh {i:02d} | {n} | {title}\n')
        f.write('\nHINH CHUA TAO (DU LIEU THIEU / KHONG TUONG THICH):\n')
        for i,err in c.skipped:f.write(f'Hinh {i:02d} | {err}\n')
    with (c.out/'danh_sach_chen_hinh.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.writer(f);w.writerow(['So hinh','File anh','Trang thai','Chu thich / Ly do'])
        items=([(i,n,'DA TAO',t) for i,n,t in c.success] +
               [(i,'','CHUA TAO',e) for i,e in c.skipped])
        for item in sorted(items,key=lambda x:x[0]):w.writerow(item)
    print(f'\nHOAN THANH: {len(c.success)}/21 hinh -> {c.out}')
    print('Xem log_tao_hinh.txt va danh_sach_chen_hinh.csv de biet hinh nao can them du lieu.')


def main():
    ap=argparse.ArgumentParser(description='Ve 21 hinh cho bao cao UTKFace, dung cay thu muc da gui')
    ap.add_argument('--root', type=Path, default=Path(__file__).resolve().parent,
                    help='D: root chua A0-A12(Sqrt) va A12(NoSqrt); mac dinh la thu muc cua Anh.py')
    ap.add_argument('--out',type=Path,default=None,help='Mac dinh: ROOT/Anh')
    ap.add_argument('--images',type=Path,default=None,help='Thu muc anh UTKFace goc cho Hinh 18')
    args=ap.parse_args()
    root=args.root.expanduser().resolve()
    out=(args.out.expanduser().resolve() if args.out else root/'Anh')
    out.mkdir(parents=True,exist_ok=True)
    paths=get_listpaths(root)
    # Prefer the exact branch in folder_structure.txt, never take unrelated summaries.
    all_paths=[p for p in paths if p.name.lower()=='all_runs.csv' and source_variant(p)=='Sqrt']
    all_paths.sort(key=lambda p:(p.parent.name.lower()!='summary',len(str(p))))
    all_path=all_paths[0] if all_paths else None
    no_paths=[p for p in paths if p.name.lower()=='test_by_seed.csv' and source_variant(p)=='NoSqrt']
    no_paths.sort(key=lambda p:len(str(p)))
    no_path=no_paths[0] if no_paths else None
    d=pd.DataFrame();no=pd.DataFrame()
    if all_path:
        try:d=normalize_runs(read_table(all_path))
        except Exception as e:print('[WARN] Cannot parse main all_runs:',e)
    if no_path:
        try:no=normalize_runs(read_table(no_path),default_method='NoSqrt')
        except Exception as e:print('[WARN] Cannot parse NoSqrt test_by_seed:',e)
    if not no.empty:
        no['method']='NoSqrt'
        no['split']='test'
    # Secondary read: per-run JSON metrics fills validation/train and missing summaries.
    extra=extract_json_run_rows(root)
    extra_main=extra[extra.method!='NoSqrt'].copy() if not extra.empty else pd.DataFrame()
    extra_no=extra[extra.method=='NoSqrt'].copy() if not extra.empty else pd.DataFrame()
    d=merge_runs(d,extra_main)
    no=merge_runs(no,extra_no)
    d=d[d.method.isin(METHODS_MAIN)].copy() if not d.empty else d
    no=no[no.method=='NoSqrt'].copy() if not no.empty else no
    print('ROOT:',root)
    print('Main summary:',all_path,'| combined rows:',len(d))
    print('NoSqrt summary:',no_path,'| combined rows:',len(no))
    print('Run JSON fallback rows:',len(extra),'| Output:',out)
    ctx=Context(root,out,paths,d,no,args.images)
    run_all(ctx)

if __name__=='__main__':
    main()
