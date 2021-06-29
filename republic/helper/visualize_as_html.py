class DisplayFragments(object):
    def __init__(self, mtext=None, tps=[]):
        self.types = mtext.types
        self.mtext = mtext
        self.template = "<div>{}</div><hr>"
        self.set_colormap()

    def set_colors(self, schema):
        self.colorscheme = schema

    def get_schema(self):
        out = [self.template.format("overview of types and colors:")]
        for item in self.types:
            color = self.colormap[item]
            outtxt = self.mtmpl.format(color=color, tp=item, txt=item)
            out.append(self.template.format(outtxt))
        return ("\n\n".join(out))

    def set_colormap(self, schema=[]):
        if schema == []:  # brewer paired scheme is default, but can be overridden
            schema = ['rgb(166,206,227)',
                      'rgb(31,120,180)',
                      'rgb(178,223,138)',
                      'rgb(51,160,44)',
                      'rgb(251,154,153)',
                      'rgb(227,26,28)',
                      'rgb(253,191,111)',
                      'rgb(255,127,0)',
                      'rgb(202,178,214)',
                      'rgb(106,61,154)',
                      'rgb(255,255,153)',
                      'rgb(177,89,40)']
        try:
            self.colormap = {k[1]: schema[k[0]] for k in enumerate(self.types)}
        except IndexError:  # too many types
            print("too many types")

    def color_match(self, ftype):
        color = self.colormap.get(ftype)
        return color

    def color_fragment(self, fragment, tp, color):
        cfragment = self.mtmpl.format(color=color, tp=tp, txt=fragment)
        return cfragment

    def display_to_html(self, with_images=False):
        if with_images == True:
            self.mtmpl = """<span style="color:{color}"><img src="images/{tp}.png" height="24px">{txt}</span>"""
        else:
            self.mtmpl = """<span style="color:{color}">{txt}</span>"""
        fragments = self.mtext.get_fragments()
        # fragment += "[{}]".format(i.idnr) # for now
        outfragments = []
        for fragment in fragments:
            if fragment[0] != 'unmarked':
                tp = fragment[0]
                # if tp != 'president':
                #     tp = 'delegate'
                tcolor = self.color_match(tp) or 'unknown'
                ff = self.color_fragment(color=tcolor, tp=tp, fragment=fragment[1])
                outfragments.append(ff)
            else:
                outfragments.append(fragment[1])
        txt = " ".join(outfragments)  # may want to turn this in object property
        return txt

    def __repr__(self):
        return self.display_to_html()


def as_html(presentielijsten):
    out = []
    for key in presentielijsten.keys():
        frob = presentielijsten[key].matched_text
        h = DisplayFragments(frob)
        p = h.display_to_html()
        out.append("<dl><dt>%s</dt><dd>%s</dd></dl><hr>" % (key, p))
    out.insert(0, h.get_schema())
    outhtml = "\n\n".join(out)
    return outhtml
