from typing import List, Optional

import torch
import torch.nn as nn


class FeatureEmbedder(nn.Module):
    def __init__(
        self,
        cardinalities: List[int],
        embedding_dims: List[int],
    ) -> None:
        super().__init__()

        self.__num_features = len(cardinalities)

        def create_embedding(c: int, d: int) -> nn.Embedding:
            embedding = nn.Embedding(c, d)
            return embedding

        self.__embedders = nn.ModuleList(
            [
                create_embedding(c, d)
                for c, d in zip(cardinalities, embedding_dims)
            ]
        )

    def forward(self, features: torch.Tensor) -> torch.Tensor:
        if self.__num_features > 1:
            # we slice the last dimension, giving an array of length
            # self.__num_features with shape (N,T) or (N)
            cat_feature_slices = torch.chunk(
                features, self.__num_features, dim=-1
            )
        else:
            cat_feature_slices = [features]

        return torch.cat(
            [
                embed(cat_feature_slice.squeeze(-1))
                for embed, cat_feature_slice in zip(
                    self.__embedders, cat_feature_slices
                )
            ],
            dim=-1,
        )


class FeatureAssembler(nn.Module):
    def __init__(
        self,
        T: int,
        embed_static: Optional[FeatureEmbedder] = None,
        embed_dynamic: Optional[FeatureEmbedder] = None,
    ) -> None:
        super().__init__()

        self.T = T
        self.embeddings = nn.ModuleDict(
            {"embed_static": embed_static, "embed_dynamic": embed_dynamic}
        )

    def forward(
        self,
        feat_static_cat: torch.Tensor,
        feat_static_real: torch.Tensor,
        feat_dynamic_cat: torch.Tensor,
        feat_dynamic_real: torch.Tensor,
    ) -> torch.Tensor:
        processed_features = [
            self.process_static_cat(feat_static_cat),
            self.process_static_real(feat_static_real),
            self.process_dynamic_cat(feat_dynamic_cat),
            self.process_dynamic_real(feat_dynamic_real),
        ]

        return torch.cat(processed_features, dim=-1)

    def process_static_cat(self, feature: torch.Tensor) -> torch.Tensor:
        if self.embeddings["embed_static"] is not None:
            feature = self.embeddings["embed_static"](feature)
        return feature.unsqueeze(1).expand(-1, self.T, -1).float()

    def process_dynamic_cat(self, feature: torch.Tensor) -> torch.Tensor:
        if self.embeddings["embed_dynamic"] is None:
            return feature.float()
        else:
            return self.embeddings["embed_dynamic"](feature)

    def process_static_real(self, feature: torch.Tensor) -> torch.Tensor:
        return feature.unsqueeze(1).expand(-1, self.T, -1)

    def process_dynamic_real(self, feature: torch.Tensor) -> torch.Tensor:
        return feature
