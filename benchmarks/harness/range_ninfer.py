from range_tuner import *
variant=sys.argv[1]if len(sys.argv)>1 else'nvfp4full'
key='27b_ninfer'if variant=='nvfp4full'else'huihui_'+variant+'_ninfer'
old=read(W/('quiet-ninfer-nvfp4full-old-90.json'if variant=='nvfp4full'else'quiet-ninfer-huihui-'+variant+'-old-90.json'))
base=latest(old,'ninfer')
native=copy.deepcopy(base);native['command'][3]=str(R/'build/ninfer-latest-native/apps/ninfer-serve');native['engine_variant']='native120';opt(native,'--device-profile-path',W/('ninfer-device-profile-latest-native-performance.json'if current_environment()else'ninfer-device-profile-latest-native.json'))
candidates=[]
for backend,config in [('compatible',base),('native',native)]:
 for tag,changes in [('k7-chunk512',{}),('k7-chunk1024',{'--prefill-chunk':1024}),('mtp3',{'--spec':'mtp','--draft-tokens':3}),('plain',{'--spec':'none','--draft-tokens':None})]:
  candidates.append((backend+'-'+tag,changed(config,changes)))
 graph=copy.deepcopy(config)
 if '--no-cuda-graph'in graph['command']:graph['command'].remove('--no-cuda-graph')
 candidates.append((backend+'-k7-graphs',graph))
 subset=copy.deepcopy(config)
 if '--full-draft-head'in subset['command']:subset['command'].remove('--full-draft-head')
 candidates.append((backend+'-subset512',subset))
tune(key,base,'qwen27b',candidates,[('chunk1024',{'--prefill-chunk':1024}),('chunk2048',{'--prefill-chunk':2048})],[],old=old,cache=False,low_configs=candidates)

