class GraphQLContext:
    def __init__(self, dataloaders, requires_serializable):
        self.dataloaders = dataloaders
        self.requires_serializable = requires_serializable
