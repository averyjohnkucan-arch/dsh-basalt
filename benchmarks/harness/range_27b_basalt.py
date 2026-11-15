from range_tuner import *
base=read(W/'latest-27b-basalt-dflash-probe.json')
fits=[]
for resident in [65536,98304,114688,131072,147456,163840,0]:
 c=changed(base,{'--kv-resident':resident})
 probe=run(c,'27b-basalt-memory-fit-'+str(resident),'qwen27b','code',n=64,role='startup memory-fit only; not qualified throughput')
 fits.append(dict(resident=resident,status=probe['status'],case=name(probe),error=probe.get('error')))
save('27b_basalt_memory_fits',fits)
successful=[x['resident']for x in fits if x['status']=='ok']
if successful:opt(base,'--kv-resident',0 if 0 in successful else max(successful))
candidates=[]
for tag,changes in [('spec6',{'--spec':6}),('spec4',{'--spec':4}),('spec0',{'--spec':0}),('resident8k',{'--kv-resident':8192}),('resident32k',{'--kv-resident':32768}),('resident64k',{'--kv-resident':65536}),('resident96k',{'--kv-resident':98304}),('resident112k',{'--kv-resident':114688}),('resident128k',{'--kv-resident':131072}),('plain-resident128k',{'--spec':0,'--kv-resident':131072})]:
 candidates.append((tag,changed(base,changes)))
tune('27b_basalt',base,'qwen27b',candidates,[],[(f'spec{s}',{'--spec':s})for s in [0,4,6,8]])
