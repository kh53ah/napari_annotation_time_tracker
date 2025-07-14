from napari.layers import Labels

def set_editable_all_layers(viewer, state: bool):
    """Sperrt oder erlaubt Annotation auf allen editierbaren Layern."""
    for layer in viewer.layers:
        if hasattr(layer, 'editable'):
            layer.editable = state

def lock_labels_layers(viewer):
    """Schaltet Labels-Layer in den Pan-Modus (nicht bearbeitbar)."""
    for layer in viewer.layers:
        if isinstance(layer, Labels):
            layer.mode = 'pan_zoom'

def unlock_labels_layers(viewer):
    """Setzt Labels-Layer zurück in den Mal-Modus (z. B. paint)."""
    for layer in viewer.layers:
        if isinstance(layer, Labels):
            layer.mode = 'paint' #ACHTUNG anpassen?