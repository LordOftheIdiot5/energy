import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from atlas_vector_tiles import project,band,tile_records
class AtlasTilesTests(unittest.TestCase):
    def test_projection_and_bands(self):
        self.assertEqual(project(0,0),(.5,.5))
        self.assertLess(project(180,-30)[0],1)
        self.assertIsNone(project(0,89))
        self.assertEqual([band(x) for x in [None,0,10,100,1000]],["unknown","0-9","10-99","100-999","1000+"])
    def test_group_accounting_and_detail(self):
        rows=[({"id":str(i),"name":"Example","fuel":"Solar","country":"NOR","capacity_mw":mw},project(0,0)) for i,mw in enumerate([None,0,1,10])]
        for z in [0,4,5,8]:
            features=[f["properties"] for _,_,layer in tile_records(rows,z) for f in layer["features"]]
            self.assertEqual(sum(p["count"] for p in features),4)
            if z<=4:self.assertEqual(len(features),3);self.assertEqual(sum(p["known_capacity_count"] for p in features),3)
            else:self.assertEqual({p["id"] for p in features},{"0","1","2","3"});self.assertNotIn("capacity_mw",features[0])
