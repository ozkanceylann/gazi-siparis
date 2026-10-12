import base64,json,mimetypes,pathlib,sys
root=pathlib.Path(__file__).resolve().parents[1];assets={}
for p in (root/'web').rglob('*'):
 if not p.is_file():continue
 name=p.relative_to(root/'web').as_posix();raw=p.read_bytes()
 if name=='index.html':raw=raw.decode().replace('<script src="app.js" defer>','<script src="runtime-config.js"></script><script src="app.js" defer>').encode()
 assets[name]={'type':mimetypes.guess_type(name)[0] or 'application/octet-stream','content':base64.b64encode(raw).decode()}
assets['runtime-config.js']={'type':'application/javascript','content':base64.b64encode(b'window.GAZI_HOSTED=true;').decode()}
output=pathlib.Path(sys.argv[1]);output.parent.mkdir(parents=True,exist_ok=True);output.write_text((root/'hosting/worker-template.js').read_text().replace('__ASSETS__',json.dumps(assets,separators=(',',':'))))
