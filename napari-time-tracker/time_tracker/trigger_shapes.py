from napari import viewer

class TriggerShapeTimer:

    def check_layer(self):
        selection = viewer.layers.selection
        if(len(selection) > 1):
            return False
        selected_layer = selection[0]
        if(selected_layer.type != 'Shapes'):
            return False
        return True


