import math
import parser

class RenderError(Exception):
  pass

# Global options passed in a dictionary:
# offset: (x,y) tuple (in viewport units) that will be added to passed coordinates
# scale: for what a viewport unit maps to, in TikZ units
# extra_args: list of strings, extra TikZ options to use in statements

# VERY LOW LEVEL
# TikZ syntax for coordinates, points...

def render_tikz_length(length, options):
  return u"%.4f" % (length * options["scale"])

def render_tikz_vector(vector, options):
  assert len(vector) == 2
  vector = (vector[0], -vector[1])
  return u"(%s,%s)" % tuple(map(lambda x: render_tikz_length(x, options), vector))

def render_tikz_point(point, options):
  vector = point[0] + options["offset"][0], point[1] + options["offset"][1]
  return render_tikz_vector(vector, options)

def render_tikz_statement(arguments, content, options):
  arguments = options["extra_args"] + arguments
  return u"  \\draw[%s] %s;\n" % (u", ".join(arguments), content)

def render_tikz_comment(comment, options):
  return u"  %% %s\n" % (comment,)

REGULAR_ESCAPES = u"&%$#_{}"
SPECIAL_ESCAPES = {u"\\": u"textbackslash", u"^": u"textasciicircum", u"~": u"textasciitilde"}
def escape_latex_char(c):
  if c in REGULAR_ESCAPES: return "\\" + c
  if c in SPECIAL_ESCAPES: return "\\" + SPECIAL_ESCAPES[c]
  return c

def render_tikz_text(text, options):
  return "".join(map(escape_latex_char, text))

# GRAPHIC SHAPES
# Renders one TikZ statement for a passed graphic shape

#TODO: remove
def draw_test_point(point, options):
  if isinstance(point, parser.Point): point = (point.x, point.y)
  return "  \\filldraw[gray] %s circle [radius=2pt];\n" % render_tikz_point(point, options)

def render_graphic_object(object, options):

  if isinstance(object, parser.Text):
    bounds = object.bounds
    bold = object.font.bold
    text = render_tikz_text(object.text, options)
    vertical = object.vertical

    if vertical: arguments.append("rotate=-90")
    if bold: text = "\textsf{%s}" % text
    center = ((bounds.x1+bounds.x2) / 2.0, (bounds.y1+bounds.y2) / 2.0)
    arguments = []
    contents = "%s node[%s] {%s}" % (render_tikz_point(center, options), ", ".join(arguments), text)
    return render_tikz_statement([], contents, options)

  if isinstance(object, parser.Line):
    p1, p2 = object.p1, object.p2
    contents = "%s -- %s" % (render_tikz_point((p1.x, p1.y), options), render_tikz_point((p2.x, p2.y), options))
    arguments = []
    # TODO: line_width
    return render_tikz_statement(arguments, contents, options)

  if isinstance(object, parser.Arc):
    bounds = object.bounds
    center = ((bounds.x1+bounds.x2) / 2.0, (bounds.y1+bounds.y2) / 2.0)
    radius = (abs(bounds.x1-bounds.x2) / 2.0, abs(bounds.y1-bounds.y2) / 2.0)

    p1 = (object.p1.x, object.p1.y)
    p2 = (object.p2.x, object.p2.y)
    dp1 = ((p1[0]-center[0])/radius[0], -(p1[1]-center[1])/radius[1])
    dp2 = ((p2[0]-center[0])/radius[0], -(p2[1]-center[1])/radius[1])

    angle1 = math.degrees(math.atan2(dp1[1], dp1[0]))
    angle2 = math.degrees(math.atan2(dp2[1], dp2[0]))
    mod1 = math.sqrt(dp1[0]**2 + dp1[1]**2)
    mod2 = math.sqrt(dp2[0]**2 + dp2[1]**2)

    np1 = (dp1[0]/mod1 * radius[0] + center[0], -dp1[1]/mod1 * radius[1] + center[1])
    np2 = (dp2[0]/mod2 * radius[0] + center[0], -dp2[1]/mod2 * radius[1] + center[1])

    contents = "%s arc[x radius=%s, y radius=%s, start angle=%.1f, end angle=%.1f]" % ( \
      render_tikz_point(np1, options), \
      render_tikz_length(radius[0], options), \
      render_tikz_length(radius[1], options), \
      angle1, angle2, \
    )
    arguments = []
    # TODO: line_width
    return render_tikz_statement(arguments, contents, options)

  if isinstance(object, parser.Rectangle):
    bounds = object.bounds
    start = (bounds.x1, bounds.y1)
    end = (bounds.x2, bounds.y2)
    contents = "%s rectangle %s" % (render_tikz_point(start, options), render_tikz_point(end, options))
    arguments = []
    # TODO: line_width
    return render_tikz_statement(arguments, contents, options)

  if isinstance(object, parser.Circle):
    bounds = object.bounds
    center = ((bounds.x1+bounds.x2) / 2.0, (bounds.y1+bounds.y2) / 2.0)
    radius = (abs(bounds.x1-bounds.x2) / 2.0, abs(bounds.y1-bounds.y2) / 2.0)
    contents = "%s circle[x radius=%s, y radius=%s]" % ( \
      render_tikz_point(center, options), \
      render_tikz_length(radius[0], options), \
      render_tikz_length(radius[1], options), \
    )
    arguments = []
    # TODO: line_width
    return render_tikz_statement(arguments, contents, options)

# SCHEMATIC SHAPES
# Renders TikZ statements for a passed schematic object
# Highest level possible, prints warnings etc.
# TODO: support transformations

# Parsing and formatting node names

def _prepare_node_name_parser():
  from pyparsing import Suppress, Regex, OneOrMore, Optional, Group
  decimal = Regex("\d+").setParseAction(lambda t: int(t[0]))
  subscript_contents = decimal + Optional(Suppress("..") + decimal)
  subscript = Group(Suppress("[") + subscript_contents + Suppress("]")).setParseAction(lambda x: tuple(x[0]))
  component_name = Regex("\w+")
  component = Group(component_name + Optional(subscript)) \
    .setParseAction(lambda x: (x[0][0], x[0][1] if len(x[0]) > 1 else None))
  return OneOrMore(component)

node_name_parser = _prepare_node_name_parser()

def parse_node_name(name):
  """ Parse name in Quartus notation, returning a list of (name, subscript) tuples,
      where subscript is either None (no subscript found), or a (start[, end]) tuple. """
  return node_name_parser.parseString(name, parseAll=True).asList()

def get_type_width(parsed_name):
  get_component_width = lambda x: abs(x[1][0]-x[1][1])+1 if x[1] and len(x[1]) > 1 else 1
  return sum(map(get_component_width, parsed_name))

def render_node_name(name, options):
  def render_component(component):
    name, subscript = component
    output = render_tikz_text(name, options)
    if subscript:
      output += "..".join(subscript)
    return output
  return " ".join(map(render_component, parse_node_name(name)))

# Line rendering

def render_all_lines(lines, options):
  # It's important to draw series of connectors "in a single run",
  # rather than many segments, so group them in runs, where each
  # run is a (point list, width) tuple
  runs = []

  def process_end(run):
    point = run[0][-1]
    neighbors = []

    def process(line):
      sides = {line[0], line[1]}
      if point not in sides: return True

      sides.remove(point)
      neighbors.append(iter(sides).next())
      if line[2] and run[1][0] and line[2] != run[1][0]:
        print "WARNING: widths inconsistent on point %s" % point
      else:
        run[1][0] = line[2]
      return False
    lines[:] = [line for line in lines if process(line)]

    if len(neighbors) == 1:
      run[0].append(neighbors[0])
      return process_end(run)
    for neighbor in neighbors:
      start_run(point, neighbor, run[1])

  def start_run(start, to, width):
    run = ([start, to], width)
    runs.append(run)
    process_end(run)
    return run

  while len(lines):
    line = lines.pop()
    run = start_run(line[0], line[1], [line[2]])
    run[0].reverse()
    process_end(run)

  return "".join(map(lambda x: render_line_run(x,options), runs))

def render_line_run(run, options):
  points, width = run
  width = width[0]
  if width is None:
    print "WARNING: No known type for %s run, defaulting to node" % str(points[0])
    width = 1
  assert len(points) >= 2 and width >= 1
  contents = " -- ".join(map(lambda x: render_tikz_point(x, options), points))
  arguments = [("node" if width == 1 else "bus") + " line"]
  return render_tikz_statement(arguments, contents, options)

# Pin rendering

def render_pin(lines, pin, options):
  name = pin.name.text
  if pin.direction == "output":
    connection = (52,8)
    text_point = (82,8)
    text_anchor = "west"
    drawing = [(52,4), (78,4), (82,8), (78,12), (52,12)]
  elif pin.direction == "input":
    connection = (121,8)
    text_point = (92,8)
    text_anchor = "east"
    drawing = [(92,12), (117,12), (121,8), (117,4), (92,4)]
  else:
    print "WARNING: don't know how to render %s pin drawing" % pin.direction
    return None

  noptions = dict(options)
  noptions["offset"] = (options["offset"][0] + pin.bounds.x1, options["offset"][1] + pin.bounds.y1)
  statements = []

  connection = (connection[0] + pin.bounds.x1, connection[1] + pin.bounds.y1)
  width = get_type_width(parse_node_name(name))
  lines.append((connection, (pin.p.x, pin.p.y), width))

  contents = " -- ".join(map(lambda x: render_tikz_point(x, noptions), drawing) + ["cycle"])
  arguments = [pin.direction + " pin"]
  statements.append(render_tikz_statement(arguments, contents, noptions))

  contents = "%s node[anchor=%s] {%s}" % ( \
    render_tikz_point(text_point, noptions), \
    text_anchor, \
    render_node_name(name, noptions), \
  )
  arguments = ["pin text"]
  statements.append(render_tikz_statement(arguments, contents, noptions))

  return "".join(statements)

# Symbol rendering

def render_symbol(lines, symbol, options):
  statements = []
  return "".join(statements)

# Little things: connectors, junctions, drawings

def render_drawing(objects, options):
  statements = [render_graphic_object(o, options) for o in objects if not o.invisible]
  return "".join(statements)

def add_connector(lines, connector, options):
  p1 = (connector.p1.x, connector.p1.y)
  p2 = (connector.p2.x, connector.p2.y)
  lines.append((p1, p2, None))
  # FIXME: it'd be nice to verify, at the end, that bus matched width

def render_junction(junction, options):
  p = (junction.p.x, junction.p.y)
  contents = "%s node[contact] {}" % (render_tikz_point(p, options),)
  arguments = ["junction"]
  return render_tikz_statement(arguments, contents, options)
