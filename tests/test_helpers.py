from helpers import encode_bencode, decode_bencode
import unittest


class TestCase(unittest.TestCase):

    def test_encode_bencode(self):
        assert encode_bencode(None) == ""        
        assert encode_bencode("") == "0:"
        assert encode_bencode([]) == "le"
        assert encode_bencode({}) == "de"

        assert encode_bencode(1) == "i1e"
        assert encode_bencode(-1) == "i-1e"
        assert encode_bencode(0) == "i0e"
        assert encode_bencode("foo") == "3:foo"

        assert encode_bencode([1]) == "li1ee"
        assert encode_bencode(["foo"]) == "l3:fooe"
        assert encode_bencode([1, "foo"]) == "li1e3:fooe"
        assert encode_bencode({"foo": 1}) == "d3:fooi1ee"

        assert encode_bencode([1, ["foo"]]) == "li1el3:fooee"
        assert encode_bencode({"foo": [1]}) == "d3:fooli1eee"
        assert encode_bencode([{"foo": 1}]) == "ld3:fooi1eee"
        assert encode_bencode({"foo": {"bar": "baz"}}) == "d3:food3:bar3:bazee"

    def test_decode_bencode(self):
        assert decode_bencode("") == None
        assert decode_bencode("0:") == ""
        assert decode_bencode("le") == []
        assert decode_bencode("de") == {}
        assert decode_bencode("i1e") == 1
        assert decode_bencode("i-1e") == -1
        assert decode_bencode("i0e") == 0
        assert decode_bencode("3:foo") == "foo"
        assert decode_bencode("li1ee") == [1]
        assert decode_bencode("l3:fooe") == ["foo"]
        assert decode_bencode("li1e3:fooe") == [1, "foo"]
        assert decode_bencode("d3:fooi1ee") == {"foo": 1}
        assert decode_bencode("li1el3:fooee") == [1, ["foo"]]
        assert decode_bencode("d3:fooli1eee") == {"foo": [1]}
        assert decode_bencode("ld3:fooi1eee") == [{"foo": 1}]
        assert decode_bencode("d3:food3:bar3:bazee") == {"foo": {"bar": "baz"}}
