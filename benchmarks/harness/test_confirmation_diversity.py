"""Actual candidate selection: duplicate CLI/cache paths cannot consume confirmations."""
from pathlib import Path
import copy,hashlib,json
from range_tuner import confirmation_configs
R=Path('/mnt/media/scratch/dsh-inference-tuning-20261115')
def config(spec):return dict(command=['taskset','-c','0-21','fixture-engine','--spec',str(spec),'--expert-profile','/source/ranking.prof'],engine_binary_sha256='engine-sha')
def result(c):return dict(status='ok',config=c)
base=config(8);six=config(6);four=config(4);duplicate=copy.deepcopy(six);duplicate['expert_profile_source']='/source/ranking.prof';duplicate['command'][-1]='/case/input-expert-profile.bin';duplicate['command']+=['--draft-log','/case/draft.log']
screens=[(result(base),'already-full',base),(result(six),'spec6',six),(result(duplicate),'same6-new-case',duplicate),(result(four),'spec4',four)]
chosen=confirmation_configs(screens,result(base));assert [tag for tag,_ in chosen]==['spec6','spec4']
assert confirmation_configs(screens[:1],result(base))==[]
assert len(confirmation_configs(screens,result(base),limit=1))==1
assert confirmation_configs(screens,result(base),limit=0)==[]
record=dict(status='passed',scope='Actual confirmation helper with normalized native identities. Existing full baseline and duplicate settings with owned expert-profile/log paths are excluded; next distinct settings receive the two confirmations. No GPU or model speed claim.',source_sha256=hashlib.sha256((R/'work/range_tuner.py').read_bytes()).hexdigest(),selected=[tag for tag,_ in chosen],already_measured_only=[],single_limit=1,zero_limit=0)
(R/'outputs/confirmation-candidate-diversity-test.json').write_text(json.dumps(record,indent=2)+'\n');print('Distinct confirmation-candidate checks passed')
