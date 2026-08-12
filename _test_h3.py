import sys, json, traceback
sys.path.insert(0, '.')

from core.llm_client import LLMClient
from core.storyboard import generate_storyboard_h3

with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

llm_provider = config.get('llm', {}).get('provider', 'agnes')
llm_config = config.get('llm', {}).get('providers', {}).get(llm_provider, {})
print(f'LLM provider: {llm_provider}')
print(f'LLM model: {llm_config.get("model")}')

llm = LLMClient(
    base_url=llm_config.get('base_url', ''),
    api_key=llm_config.get('api_key', ''),
    model=llm_config.get('model', ''),
)

try:
    sb = generate_storyboard_h3(
        llm=llm,
        product_name='测试饼干',
        product_desc='酥脆黄油饼干',
        selling_points='酥脆可口',
        template=None,
        frame_count=3,
        total_duration=6,
        product_info=None,
        direction='',
        on_plan_chunk=lambda t: None,
        on_frame_chunk=lambda t: None,
        on_frame_done=lambda n, f: print(f'  frame {n} done'),
        on_stage=lambda s: print(f'  stage: {s}'),
    )
    print(f'Success: {len(sb.frames)} frames')
    for f in sb.frames:
        print(f'  Frame {f.frame}: {f.shot_label} {f.cut_timestamp} dur={f.duration} imd={len(f.integrated_multimodal_description)}chars')
    print(f'  overall_soundscape: {sb.overall_soundscape[:80] if sb.overall_soundscape else "(empty)"}')
    print(f'  non_diegetic_music: {sb.non_diegetic_music[:80] if sb.non_diegetic_music else "(empty)"}')
except Exception as e:
    traceback.print_exc()
