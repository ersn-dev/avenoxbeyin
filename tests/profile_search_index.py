#!/usr/bin/env python3
"""Reproduce frozen cold search indexing and attribute its time to IO/SQLite.

No production code is modified, test thresholds remain unchanged, and the
original ingest/validation/transaction code is executed.
"""
from contextlib import contextmanager
import json
from pathlib import Path
import sys
import tempfile
from time import perf_counter
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'template/.claude/scripts'))
import evaluate_v3_search as evaluator
import beyin_v3 as runtime


def run_once(index):
    fixture,_=evaluator.read_fixture()
    tallies={name:dict(calls=0,seconds=0.0) for name in
             ('initialize','initialize_connect','ingest','validate','connect','seed_total')}
    def measure(name,work):
        start=perf_counter()
        try:return work()
        finally:
            tallies[name]['seconds']+=perf_counter()-start
            tallies[name]['calls']+=1

    original_initialize=runtime.MemoryStore.__init__
    initializing=False
    def initialize(self,*args,**kwargs):
        nonlocal initializing
        initializing=True
        try:
            return measure('initialize',lambda:original_initialize(self,*args,**kwargs))
        finally:
            initializing=False

    original_validate=runtime.MemoryStore._validate
    original_connect=runtime.MemoryStore._connect
    original_ingest=runtime.MemoryStore.ingest
    def validate(self,*args,**kwargs):
        return measure('validate',lambda:original_validate(self,*args,**kwargs))
    @contextmanager
    def connect(self,*args,**kwargs):
        phase='initialize_connect' if initializing else 'connect'
        start=perf_counter()
        try:
            with original_connect(self,*args,**kwargs) as db:
                yield db
        finally:
            tallies[phase]['seconds']+=perf_counter()-start
            tallies[phase]['calls']+=1
    def ingest(self,*args,**kwargs):
        return measure('ingest',lambda:original_ingest(self,*args,**kwargs))

    with tempfile.TemporaryDirectory(prefix='beyin-cold-index-profile-') as tmp:
        with patch.object(runtime.MemoryStore,'__init__',initialize),patch.object(runtime.MemoryStore,'_validate',validate),patch.object(
                runtime.MemoryStore,'_connect',connect),patch.object(
                runtime.MemoryStore,'ingest',ingest):
            store,cold=evaluator.seed_store(runtime,Path(tmp),fixture)
        # Cold index excludes construction; initialize/initialize_connect are separate.
        # Phase scopes are inclusive: connect includes SQL work, commit and close;
        # ingest includes validation and connect. Do not add these phase times.
        # Original cold index includes file writes + one transaction per record.
        # The total is measured by evaluate_v3_search.seed_store unchanged.
        tallies['seed_total']={'calls':1,'seconds':cold/1000.0}
        actual=len(store._records())
        if actual!=len(fixture['records']):
            raise AssertionError('cold ingest lost records')
    return {'run':index,'records':actual,'cold_index_ms':cold,
            'phase_semantics':'inclusive; initialization excluded from cold_index_ms',
            'phases':{k:{'calls':v['calls'],'ms':round(1000*v['seconds'],2)} for k,v in tallies.items()}}


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--repeats',type=int,default=3)
    args=parser.parse_args()
    if not 1<=args.repeats<=8:parser.error('repeats out of range')
    for index in range(args.repeats):
        print('INDEX_PROFILE '+json.dumps(run_once(index),sort_keys=True),flush=True)
