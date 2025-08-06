def set_editable_all_layers(viewer, editable: bool):
    """
    Set the editable state for all layers in the viewer that support editing.

    Iterates through all layers in the given viewer and sets their `editable`
    attribute to the specified value, if they have such an attribute.

    Args:
        viewer: An object (e.g., a napari viewer) that contains a `.layers` attribute,
                which is an iterable of layer objects.
        editable (bool): The value to set for the `editable` attribute (True or False).
    """
    for layer in viewer.layers:
        if hasattr(layer, 'editable'):
            layer.editable = editable