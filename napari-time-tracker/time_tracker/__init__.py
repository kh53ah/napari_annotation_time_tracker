from magicgui import magicgui
import napari
from napari.layers import Shapes, Points, Labels, Image
from napari.utils.notifications import show_info
from .shapes_time import ShapeTimeTracker

viewer = napari.current_viewer()
stt = ShapeTimeTracker(viewer)


@magicgui
def run():
    selected = list(viewer.layers.selection)
    if not len(selected) == 1:
        show_info("Selected more than one Layer")
        pass
    if isinstance(selected[0], Points):
        pass  #Hier bitte Methode für Points einfügen
    elif isinstance(selected[0], Shapes):
        stt.shape_connect()
    elif isinstance(selected[0], Labels):
        pass  #Hier bitte Methode für Labels einfügen
    elif isinstance(selected[0], Image):
        show_info("Selected a image layer instead of an annotation layer")
        pass
    else:
        show_info("Unknown layer type")
        pass
