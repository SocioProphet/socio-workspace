#!/usr/bin/env python3
import argparse, yaml, importlib, sys, json, time
def main():
  ap=argparse.ArgumentParser(); ap.add_argument('--config',required=True); ap.add_argument('--key-metric',default=None); ap.add_argument('--dry-run',action='store_true'); a=ap.parse_args()
  cfg=yaml.safe_load(open(a.config)); task=cfg.get('task'); t0=time.time()
  if a.dry_run: result={'metrics':{'_dry_run':True}}
  else:
    mod={'embedding':'cc.runner_embeddings_hf','asr':'cc.runner_whisper_hf','vision_classification':'cc.runner_vision_onnx'}.get(task)
    if not mod: print('Unknown task',task,file=sys.stderr); sys.exit(2)
    result=importlib.import_module(mod).run(cfg)
  print(json.dumps({'task':task,'config':a.config,'elapsed_sec':round(time.time()-t0,3),'metrics':result.get('metrics',{})}, indent=2))
if __name__=='__main__': main()
