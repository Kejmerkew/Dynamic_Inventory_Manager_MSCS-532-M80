from datastructures import HashMap, Dictionary, MinHeap,CustomList

def test_get_valid_indices_matches_builtin_list_behavior():
    data = [10, 20, 30, 40]
    cl = CustomList(data)
    for i in range(-len(data), len(data)):
        assert cl.get(i) == data[i]

def test_hash_map_set_get_resize():
    m = HashMap(capacity=4, load_factor=0.75)
    for i in range(50):
        m.set(f"k{i}", i)
    for i in range(50):
        assert m.get(f"k{i}") == i
    assert len(m) == 50


def test_hash_map_delete():
    m = HashMap()
    m.set("a", 1)
    assert m.delete("a") is True
    assert m.get("a") is None
    assert m.delete("a") is False


def test_my_dict_like():
    d = Dictionary({"a": 1, "b": 2}, c=3)
    assert d["a"] == 1
    assert d.get("z") is None
    assert "b" in d

    ks = d.keys().to_py()
    vs = d.values().to_py()
    it = d.items().to_py()

    assert set(ks) == {"a", "b", "c"}
    assert set(vs) == {1, 2, 3}
    assert set(it) == {("a", 1), ("b", 2), ("c", 3)}

    native = d.to_py()
    assert native == {"a": 1, "b": 2, "c": 3}


def test_heap_push_pop_peek():
    h = MinHeap([5, 2, 9, 1])
    assert h.peek() == 1
    assert h.pop() == 1
    assert h.pop() == 2
    h.push(0)
    assert h.peek() == 0
    assert len(h) == 3