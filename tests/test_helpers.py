from helpers import encode_bencode
import unittest


class TestCase(unittest.TestCase):

    def test_encode_bencode(self):
        assert encode_bencode(None) == ""        
        assert encode_bencode("") == "0:"
        assert encode_bencode([]) == "le"
        assert encode_bencode({}) == "de"

        assert encode_bencode(1) == "i1e"
        assert encode_bencode(-1) == "i-1e"
        assert encode_bencode("foo") == "3:foo"

        assert encode_bencode([1]) == "li1ee"
        assert encode_bencode(["foo"]) == "l3:fooe"
        assert encode_bencode([1, "foo"]) == "li1e3:fooe"
        assert encode_bencode({1:"foo"}) == "di1e3:fooe"

        assert encode_bencode([1, ["foo"]]) == "li1el3:fooee"
        assert encode_bencode({1: ["foo"]}) == "di1el3:fooee"
        assert encode_bencode([{1: "foo"}]) == "ldi1e3:fooee"
