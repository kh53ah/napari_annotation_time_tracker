from magicgui import magicgui
import napari
from napari.layers import Shapes, Points, Labels, Image
from napari.utils.notifications import show_info
from napari.plugins.hook_specifications import napari_experimental_provide_dock_widget
from .shapes_time import ShapeTimeTracker


@magicgui(call_button="Start")
def run():
    viewer = napari.current_viewer()
    stt = ShapeTimeTracker(viewer)

    def on_selection_change(event):
        selected = list(viewer.layers.selection)
        if len(selected) != 1:
            show_info("Select exactly one layer")
            return

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
    viewer.layers.selection.events.changed.connect(on_selection_change)

