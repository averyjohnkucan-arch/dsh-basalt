"""The prefill tradeoff may not hide a decode regression in another genre."""
GENRES=('text','chat','story')
def prefill_safe(row,peak):
 return row['decode']>=.95*peak['decode']and all(values['decode']>=.95*peak['genres'][genre]['decode']for genre,values in row['genres'].items())
def could_improve(row,peak,winner):
 # With partial coverage the known minima are upper bounds on the final minima.
 return row['decode']>peak['decode']or(prefill_safe(row,peak)and row['prefill']>winner['prefill'])
