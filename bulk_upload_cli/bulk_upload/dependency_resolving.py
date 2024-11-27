import re
from abc import ABC, abstractmethod
from bulk_upload.models import AssetInfo, FileInfo


class DependencyResolver(ABC):
    @abstractmethod
    def resolve_dependencies(self, assets: [AssetInfo]) -> [AssetInfo]:
        pass


class EmbeddedDependencyResolver(DependencyResolver):
    def resolve_dependencies(self, assets: [AssetInfo]) -> [AssetInfo]:
        assets_dict = {asset.unity_id: asset for asset in assets}

        for asset in assets:
            for unresolved_dependency in asset.unresolved_dependencies:
                try:
                    asset.dependencies.extend(assets_dict[unresolved_dependency].files)
                except KeyError:
                    pass

        for asset in assets:
            asset.files.extend(asset.dependencies)
            asset.dependencies = []

        return assets


class AssetReferenceDependencyResolver(DependencyResolver):
    def resolve_dependencies(self, assets: [AssetInfo]) -> [AssetInfo]:
        asset_index = {}
        for i in range(len(assets)):
            asset_index[assets[i].unity_id] = i

        for asset in assets:
            for dependency in asset.unresolved_dependencies:
                if dependency in asset_index:
                    asset.dependencies.append(asset_index[dependency])

        return assets


class DefaultDependencyResolver(DependencyResolver):
    def resolve_dependencies(self, assets: [AssetInfo]) -> [AssetInfo]:
        return assets