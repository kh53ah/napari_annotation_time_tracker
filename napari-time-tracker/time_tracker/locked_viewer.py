def set_editable_all_layers(viewer, editable):
    """
    Sets the editable state for all layers in the Napari viewer.
    """
    for layer in viewer.layers:
        layer.editable = editable