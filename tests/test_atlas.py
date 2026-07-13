import base64
import unittest
from actool_linux.atlas import AtlasKeyToken, AtlasLink, build_atlas_link, parse_atlas_link, build_packed_atlas_car
from actool_linux.bom import BOMStore
from actool_linux.car import CARFile

P1=base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
P2=base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAQAAADYv8WvAAAAEklEQVR4nGPg/m/wiCH0aNUKABRABFncH0e8AAAAAElFTkSuQmCC")

class AtlasTests(unittest.TestCase):
    def test_oracle_link_roundtrip(self):
        raw=bytes.fromhex("4b4c4e4900000000a2000000020000000d0000000f000000000018000000010009000200b50008005c020c0001001900050000000000")
        link=parse_atlas_link(raw)
        self.assertEqual((link.x,link.y,link.width,link.height),(162,2,13,15))
        self.assertEqual(link.tokens,(AtlasKeyToken(24,0),AtlasKeyToken(1,9),AtlasKeyToken(2,181),AtlasKeyToken(8,604),AtlasKeyToken(12,1),AtlasKeyToken(25,5)))
        self.assertEqual(link.variant, "generic")
        self.assertEqual(build_atlas_link(link),raw)

    def test_explicit_packed_asset_link_roundtrip(self):
        raw = bytes.fromhex("4b4c4e4900000000020000000200000040000000400000000c0014000000010009000200b5000c0001001100626e00000000")
        link = parse_atlas_link(raw)
        self.assertEqual((link.x, link.y, link.width, link.height), (2, 2, 64, 64))
        self.assertEqual(link.variant, "explicit")
        self.assertEqual((link.header_u16, link.header_u32), (12, 20))
        self.assertEqual(link.tokens, (AtlasKeyToken(1, 9), AtlasKeyToken(2, 181), AtlasKeyToken(12, 1), AtlasKeyToken(17, 28258)))
        self.assertEqual(build_atlas_link(link), raw)

    def test_builds_linked_atlas_car(self):
        car=CARFile(BOMStore(build_packed_atlas_car({"One":P1,"Two":P2})))
        self.assertEqual(len(car.renditions),3)
        layouts=sorted(r.csi.layout for r in car.renditions)
        self.assertEqual(layouts,[1003,1003,1004])
        refs=[r for r in car.renditions if r.csi.layout==1003]
        self.assertTrue(all(len(r.csi.rendition_data)==0 for r in refs))
        links=[parse_atlas_link(next(t.value for t in r.csi.tlvs if t.tag==1010)) for r in refs]
        self.assertTrue(all(link.width>0 for link in links))
        self.assertTrue(all(next(t.value for t in link.tokens if t.attribute==25)==5 for link in links))
        self.assertTrue(all(r.key["kCRThemeDeploymentTargetName"]==5 for r in car.renditions))

    def test_splits_into_bounded_pages(self):
        car=CARFile(BOMStore(build_packed_atlas_car({"One":P1,"Two":P2},max_width=2,max_height=2)))
        self.assertEqual(sorted(r.csi.layout for r in car.renditions),[1003,1003,1004,1004])
        refs=[r for r in car.renditions if r.csi.layout==1003]
        pages=[]
        for r in refs:
            link=parse_atlas_link(next(t.value for t in r.csi.tlvs if t.tag==1010))
            pages.append(next(t.value for t in link.tokens if t.attribute==8))
        self.assertEqual(sorted(pages),[1,2])

    def test_atlas_sorting_heuristics(self):
        for h in ("name", "height", "width", "area", "max_dim"):
            car = CARFile(BOMStore(build_packed_atlas_car({"A": P1, "B": P2}, sort_by=h)))
            self.assertEqual(len(car.renditions), 3)
        with self.assertRaisesRegex(ValueError, "unsupported atlas sorting heuristic"):
            build_packed_atlas_car({"A": P1}, sort_by="invalid")
        with self.assertRaisesRegex(ValueError, "invalid atlas deployment token"):
            build_packed_atlas_car({"A": P1}, deployment_token=70000)

if __name__=='__main__': unittest.main()
