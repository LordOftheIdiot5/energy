"""Exercise archive conflict recovery using disposable local repositories; never contact live providers."""
import os,subprocess,tempfile,unittest
from pathlib import Path
SCRIPT=Path(__file__).resolve().parents[1]/"scripts/publish_fetch.sh"
class PublicationRetryTests(unittest.TestCase):
    def test_concurrent_archive_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);remote=p/"remote.git";a=p/"a";b=p/"b";binpath=p/"bin";binpath.mkdir()
            def run(args,cwd=None,env=None):
                return subprocess.run(args,cwd=cwd,env=env,check=True,capture_output=True,text=True)
            def git(cwd,*args):return run(["git",*args],cwd)
            git(p,"init","--bare","--initial-branch=main",str(remote))
            git(p,"clone",str(remote),str(a))
            for key,val in [("user.name","test"),("user.email","test@example.invalid")]:git(a,"config",key,val)
            (a/"data").mkdir();(a/"data/archive.json").write_text("base\n")
            git(a,"add","data");git(a,"commit","-m","base");git(a,"push","origin","main")
            git(p,"clone",str(remote),str(b))
            for key,val in [("user.name","test"),("user.email","test@example.invalid")]:git(b,"config",key,val)
            (b/"data/archive.json").write_text("remote revision\n");git(b,"add","data");git(b,"commit","-m","remote update");git(b,"push","origin","main")
            (a/"data/archive.json").write_text("stale candidate\n")
            fake=binpath/"python"
            fake.write_text('#!/bin/sh\nif [ "$1" = "scripts/fetch.py" ]; then printf "new observation\\n" >> data/archive.json; fi\nexit 0\n')
            fake.chmod(0o755)
            env={**os.environ,"GITHUB_ACTIONS":"true","GITHUB_RUN_ID":"12345","GITHUB_RUN_ATTEMPT":"1","PATH":str(binpath)+os.pathsep+os.environ["PATH"]}
            out=run(["bash",str(SCRIPT)],a,env)
            self.assertIn("recollecting once",out.stdout)
            git(b,"pull","--ff-only")
            self.assertEqual((b/"data/archive.json").read_text(),"remote revision\nnew observation\n")
            self.assertIn("remote update",git(b,"log","--oneline").stdout)
            self.assertNotIn("stale candidate",(b/"data/archive.json").read_text())
