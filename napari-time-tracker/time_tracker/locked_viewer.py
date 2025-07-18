def set_editable_all_layers(viewer, editable: bool):
    for layer in viewer.layers:
        if hasattr(layer, 'editable'):
            layer.editable = editable