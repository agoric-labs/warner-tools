import sys, re, gzip

# Use 'xsnap -d SNAPSHOT.xss' to dump an XS heap snapshot into a text file,
# then feed that text file into my stdin, along with a prefix. I will create
# ten files with names like "prefix-XS_M.gz" and "prefix-HEAP.gz", each with
# one section of the snapshot dump. This makes it easier to search for specific
# e.g. slots by their index number.


sections = [
    "XS_M",
    "VERS",
    "SIGN",
    "CREA", # sizes and creation parameters
    "BLOC", # the chunks table
    "HEAP", # the slots table
    "STAC",
    "KEYS", # maps ID_nnn to the property-key name
    "NAME", # helps map property-named keys, somehow
    "SYMB", # helps map symbol-named keys
    ]

prefix = sys.argv[1]
fn = None
count = 0

for line in sys.stdin:
    if sections and line.startswith(sections[0]):
        if fn:
            print(" finished %s (%d lines)" % (section, count))
            fn.close()
            count = 0
        section = sections.pop(0)
        fn = gzip.open("%s-%s.gz" % (prefix, section), "w")
        fn.write(line.encode("utf-8"))
    else:
        fn.write(line.encode("utf-8"))
    count += 1
