"""Optional draft diagnostics tolerate interleaved lines; never infer missing timings."""
import math,statistics

def parse_draft_windows(text):
 windows=[];records=malformed=0
 for line in text.splitlines():
  if not line.startswith('W '):continue
  records+=1
  try:
   fields=line.split()[1:7]
   if len(fields)!=6:raise ValueError('Incomplete window')
   row=list(map(float,fields))
   if not all(map(math.isfinite,row)):raise ValueError('Nonfinite window')
  except ValueError:
   malformed+=1;continue
  windows.append(row)
 result=dict(window_records=records,valid_window_records=len(windows),malformed_window_records=malformed,scope='Optional valid draft-window diagnostics only; malformed/interleaved rows excluded without estimating their timing')
 if windows:
  elapsed=[sum(w[3:6])for w in windows];total=sum(elapsed)
  result['windows']=dict(count=len(windows),mean_width=statistics.mean(w[0]for w in windows),mean_accepted=statistics.mean(w[1]for w in windows),mean_ms=statistics.mean(elapsed),passes_per_s=len(windows)*1000/total if total else None,draft_ms=sum(w[3]for w in windows),verify_ms=sum(w[4]for w in windows),post_ms=sum(w[5]for w in windows))
 return result
