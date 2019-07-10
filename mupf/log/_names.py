def parse_path(path):
    result = [[[]]]
    path += '\u0003'
    st_obj = 0
    st_supl = None
    in_supl= False
    for i, c in enumerate(path):
        if c == '<':
            if st_obj is not None:
                result[-1][-1].append(path[st_obj:i])
                st_obj = None
            in_supl = True
            st_supl = i
            continue
        if c == '>' and in_supl:
            in_supl = False
            result[-1][-1].append(path[st_supl+1:i])
            st_supl = None
            continue
        if c == '.' or c == '/' or c == '\u0003':
            if st_obj is not None:
                result[-1][-1].append(path[st_obj:i])
            st_obj = i+1
            if c == '.':
                result[-1].append([])
        if c == '/' or c == '\u0003':
            if c == '/':
                result.append([[]])
            st_obj = i+1
    return result

def build_path(tree):
    return "/".join([".".join([obj[0]+"".join(["<{}>".format(supl) for supl in obj[1:]]) for obj in pathpart]) for pathpart in tree])

def _make_regexp_from_filter(f):
    tree = parse_path(f)
    for pathpart in tree:
        for obj in pathpart:
            class_ = re.split(r'(\*+)', obj[0])
            class_.append('')
            for i in range(len(class_)//2):
                class_[2*i] = re.escape(class_[2*i])
                star_count = len(class_[2*i+1])
                if star_count == 1:
                    class_[2*i+1] = r'[^/.<]*'
                elif star_count == 2:
                    class_[2*i+1] = r'[^/]*'
                elif star_count == 3:
                    class_[2*i+1] = r'.*'
                elif star_count >= 4:
                    raise ValueError('too many stars')
            obj[0] = "".join(class_) + r'(?:<[^>]*>)*'
            for supl_no in range(len(obj)-1):
                obj[supl_no+1] = "<" +re.escape(obj[supl_no+1]) + r'>(?:<[^>]*>)*'
    return re.compile(build_path(tree) + r'.*')

def _append_filter(f):
    global _filters
    f = f.lstrip()
    marker = f[0]
    f = f[1:].strip()
    reg = _make_regexp_from_filter(f)
    _filters.append((marker, reg))

def _should_be_on(path):
    global _filters
    state = "-"
    for f in _filters:
        if f[1].match(path):
            state = f[0]
    return state
