import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from hydro_transfer_network import build
from nordic_observations import expanded_samples,select_samples
class EnergyAccessTests(unittest.TestCase):
    def test_network_exact_direct_edges(self):
        rows,coverage=build([{"id":11,"delfeltNr":1,"nesteDelfeltNr":2},{"id":12,"delfeltNr":2},{"id":13,"delfeltNr":3,"nesteDelfeltNr":999},{"id":14,"delfeltNr":4,"nesteDelfeltNr":4},{"id":15,"delfeltNr":5},{"id":16,"delfeltNr":5}])
        self.assertEqual(rows[0]["receivingCatchmentId"],2)
        self.assertEqual(rows[1]["sourceCatchmentIds"],[1])
        self.assertEqual(coverage,{"matched_directed_edges":1,"unresolved_or_self_edges":2,"ambiguous_ids":1})
    def test_station_rotation_retains_core(self):
        stations=[{"stationId":f"1.{i}.0","status":"Aktiv","county":"A","series":[{"parameter":1001}]} for i in range(30)]
        core={r["stationId"] for r in select_samples(stations)}
        today={r["stationId"] for r in expanded_samples(stations,"2026-11-19T00:00:00+00:00")}
        tomorrow={r["stationId"] for r in expanded_samples(stations,"2026-11-20T00:00:00+00:00")}
        self.assertTrue(core<=today and core<=tomorrow);self.assertEqual(len(today),len(core)+8);self.assertNotEqual(today,tomorrow)
