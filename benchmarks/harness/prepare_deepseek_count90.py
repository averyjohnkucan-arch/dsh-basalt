"""Create a 90% counting prompt with the same chat and reference body."""
import json
from pathlib import Path
from prepare_range_fixtures import CORPUS, framing
from deepseek_chat_turns import chat_codec
from gguf_reader import GGUFFile

work = Path(__file__).resolve().parent
gguf = next(Path('/home/user/Desktop/DeepSeek-IQ2_XXS').glob('*00001-of-00004.gguf'))
_, tokenizer = chat_codec(gguf)
metadata = GGUFFile(gguf).metadata
old_ids = json.loads((work / 'range-fixtures/deepseek-chat90.json').read_text())['ids']
prefix, old_suffix, _ = framing(tokenizer, metadata, 'chat')
count_prefix, count_suffix, _ = framing(
    tokenizer, metadata, 'chat',
    'Count from 1 to 1000 in order as numerals separated by commas. Start immediately, without commentary.',
)
assert prefix == count_prefix
assert old_ids[:len(prefix)] == prefix and old_ids[-len(old_suffix):] == old_suffix
body = tokenizer.encode(CORPUS)
length = len(old_ids) - len(prefix) - len(count_suffix)
count_ids = prefix + (body*((length+len(body)-1)//len(body)))[:length] + count_suffix
assert len(count_ids) == len(old_ids)
shared = next((index for index,(a,b) in enumerate(zip(old_ids,count_ids)) if a!=b),len(old_ids))
assert shared >= len(old_ids)-512
(work/'range-fixtures/deepseek-count90.json').write_text(json.dumps({'ids':count_ids},separators=(',',':')))
print('count prompt',len(count_ids),'shared prefix',shared)
