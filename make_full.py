import sys
import disjoint_set

'''
Usage: python make_full.py <input1> ... <inputN> <output>

Найти компоненты связности в графе пар клонов из объединения 
файлов input1, ..., inputN, и дополнить их до полных подграфов, 
записав получившийся набор пар клонов в output
'''

class progressbar:
    width = 20
    
    def __init__(self, maxval: int, startval: int):
        self.maxval = maxval
        self.val = startval
    
    def perc(self, val=None):
        if val is None:
            val = self.val
        return val / self.maxval
    
    def perc_number(self, val=None):
        return int(self.perc(val) * 100)
    
    def show(self):
        blocks = int(self.perc() * progressbar.width) 
        print(f'\r[{"#" * blocks}{"." * (progressbar.width - blocks)}]\t{self.perc_number()}%', end="")
            
    def update(self, val):
        if self.perc_number(val) > self.perc_number():
            self.val = val
            self.show()
    
    def end(self):
        print()


class codeblock:
    def __init__(self, fn: str, begin: int, end: int):
        self.fn = fn
        self.begin = begin
        self.end = end
    
    def equal(self, cb):
        return self.fn == cb.fn and self.begin == cb.begin and self.end == cb.end
    
    def __repr__(self):
        return f'{self.fn},{self.begin},{self.end}'
    
    @classmethod
    def intersect(cls, b1: "codeblock", b2: "codeblock", t: float):
        if b1.fn != b2.fn:
            return False
        ibegin, iend = max(b1.begin, b2.begin), min(b1.end, b2.end)
        ilength = iend - ibegin
        if ilength / (b1.end - b1.begin) >= t and ilength / (b2.end - b2.begin) >= t:
            return True
        return False

class clonepair:
    def __init__(self, s: str):
        dir1, fn1, begin1, end1, dir2, fn2, begin2, end2 = s.split(',')
        self.b1 = codeblock(f'{dir1},{fn1}', int(begin1), int(end1))
        self.b2 = codeblock(f'{dir2},{fn2}', int(begin2), int(end2))
    
    def __repr__(self):
        return f'{self.b1.__repr__()},{self.b2.__repr__()}'
    
    @classmethod
    def same(cls, p1: "clonepair", p2: "clonepair", t: float):
        if codeblock.intersect(p1.b1, p2.b1, t) and codeblock.intersect(p1.b2, p2.b2, t):
            return True
        if codeblock.intersect(p1.b1, p2.b2, t) and codeblock.intersect(p1.b2, p2.b1, t):
            return True
        return False

class vertex:
    def __init__(self, cb: codeblock, index: int):
        self.cb = cb
        self.index = index
        self.parent = index

class clonegraph:
    def __init__(self):
        self.vertices = []
        self.files = {}
        self.classes = disjoint_set.DisjointSet()
        self.total_edges = 0
    
    def find_copy(self, cb: codeblock):
        if cb.fn not in self.files:
            return None
        for u in self.files[cb.fn]:
            if cb.equal(self.vertices[u].cb):
                return self.vertices[u]
        return None
    
    def insert_edge(self, cp: clonepair):
        self.total_edges += 1
        v1 = self.find_copy(cp.b1)
        v2 = self.find_copy(cp.b2)
        if v1 is None:
            v1 = vertex(cp.b1, len(self.vertices))
            self.vertices.append(v1)
            if v1.cb.fn in self.files:
                self.files[v1.cb.fn].append(v1.index)
            else:
                self.files[v1.cb.fn] = [v1.index]
        if v2 is None:
            v2 = vertex(cp.b2, len(self.vertices))
            self.vertices.append(v2)
            if v2.cb.fn in self.files:
                self.files[v2.cb.fn].append(v2.index)
            else:
                self.files[v2.cb.fn] = [v2.index]
        self.classes.union(v1.index, v2.index)
        
    def write_classes(self, fn: str):
        with open(fn, "w") as f:
            for c in list(self.classes.itersets()):
                f.write('{' + ';'.join([self.vertices[v].cb.__repr__() for v in list(c)]) + '}\n')
            
    def full_to_file(self, fn: str):
        with open(fn, "w") as f:
            for c in self.classes.itersets():
                cl = list(c)
                for i in range(len(cl)):
                    for j in range(i):
                        v1 = self.vertices[cl[i]].cb
                        v2 = self.vertices[cl[j]].cb
                        f.write(f'{v1},{v2}\n')

def parse_file(fn: str):
    with open(fn, "r") as f:
        return [clonepair(line.rstrip()) for line in f]

def lines_in_file(fn: str):
    with open(fn, "rb") as f:
        num_lines = sum(1 for _ in f)
    return num_lines

def merge(ifns: list[str], ofn: str):
    total_lines = sum(lines_in_file(fn) for fn in ifns)
    current_line = 0
    progress = progressbar(total_lines, current_line)
    g = clonegraph()
    for fn in ifns:
        for x in parse_file(fn):
            current_line += 1
            progress.update(current_line)
            g.insert_edge(x)
    progress.end()
    print(f'total classes:\t{len(list(g.classes.itersets()))}')
    print(f'pairs, if make all components full:\t{sum([len(x) * (len(x) - 1) // 2 for x in g.classes.itersets()])}')
    print(f'original number of pairs:\t{g.total_edges}')
    print("Writing to file... ", end="")
    g.full_to_file(ofn)
    print("done.")
    

def main():
    ifns = sys.argv[1:-1]
    ofn = sys.argv[-1]
    merge(ifns, ofn)

if __name__ == "__main__":
    main()
