# DuoGraph3D CCF-B literature source manifest — 2026-06-28

Purpose: record the papers pulled for the CCF-B experiment package, the local PDF/text artifacts, and the official/upstream source used for later citation checks.

| paper | upstream source | local PDF | local extracted text | read status |
| --- | --- | --- | --- | --- |
| ConceptGraphs | arXiv / project baseline paper | `pdfs/conceptgraphs_arxiv.pdf` | `texts/conceptgraphs_arxiv.txt` | read for baseline framing |
| OpenMask3D | https://openmask3d.github.io/static/pdf/openmask3d.pdf | `pdfs/openmask3d_arxiv.pdf` | `texts/openmask3d_arxiv.txt` | read for proposal-first OV-3DIS baseline |
| OpenScene | CVPR 2023 / official paper | `pdfs/openscene_cvpr2023.pdf` | `texts/openscene_cvpr2023.txt` | read for dense OV semantic baseline |
| Open3DIS | https://openaccess.thecvf.com/content/CVPR2024/papers/Nguyen_Open3DIS_Open-Vocabulary_3D_Instance_Segmentation_with_2D_Mask_Guidance_CVPR_2024_paper.pdf | `pdfs/open3dis_cvpr2024.pdf` | `texts/open3dis_cvpr2024.txt` | read; proposal + 2D mask guidance |
| Open-YOLO 3D | OpenReview paper | `pdfs/open_yolo_3d_openreview.pdf` | `texts/open_yolo_3d_openreview.txt` | read; detector-label / MVPDist inspiration |
| OnlineAnySeg | https://openaccess.thecvf.com/content/CVPR2025/papers/Tang_OnlineAnySeg_Online_Zero-Shot_3D_Segmentation_by_Visual_Foundation_Model_Guided_CVPR_2025_paper.pdf | `pdfs/onlineanyseg_arxiv.pdf` | `texts/onlineanyseg_arxiv.txt` | read; online mask bank / mapping-table inspiration |
| EmbodiedSAM / ESAM | https://proceedings.iclr.cc/paper_files/paper/2025/file/5e68f9149d33a6c8ad59ed60bf90606f-Paper-Conference.pdf | `pdfs/embodiedsam_arxiv.pdf` | `texts/embodiedsam_arxiv.txt` | read; geometry-aware query lifting inspiration |
| Details Matter | https://openaccess.thecvf.com/content/ICCV2025/papers/Jung_Details_Matter_for_Indoor_Open-vocabulary_3D_Instance_Segmentation_ICCV_2025_paper.pdf | `pdfs/details_matter_iccv2025.pdf` | `texts/details_matter_iccv2025.txt` | read; recipe / false-positive filtering reference |
| OV3D-CG | https://openaccess.thecvf.com/content/ICCV2025/papers/Zhou_OV3D-CG_Open-vocabulary_3D_Instance_Segmentation_with_Contextual_Guidance_ICCV_2025_paper.pdf | `pdfs/ov3d_cg_iccv2025.pdf` | `texts/ov3d_cg_iccv2025.txt` | read; contextual reasoning reference |
| OVI-MAP | https://openaccess.thecvf.com/content/CVPR2026/papers/Deng_OVI-MAP_Open-Vocabulary_Instance-Semantic_Mapping_CVPR_2026_paper.pdf | `pdfs/ovi_map_cvpr2026.pdf` | `texts/ovi_map_cvpr2026.txt` | read; direct online mapping competitor |
| GeoGuide | https://openaccess.thecvf.com/content/CVPR2026/papers/Tao_GeoGuide_Hierarchical_Geometric_Guidance_for_Open-Vocabulary_3D_Semantic_Segmentation_CVPR_2026_paper.pdf | `pdfs/geoguide_cvpr2026.pdf` | `texts/geoguide_cvpr2026.txt` | read; hierarchical geometry-semantic consistency |
| MV3DIS | https://openaccess.thecvf.com/content/CVPR2026/papers/Zhao_MV3DIS_Multi-View_Mask_Matching_via_3D_Guides_for_Zero-Shot_3D_CVPR_2026_paper.pdf | `pdfs/mv3dis_cvpr2026.pdf` | `texts/mv3dis_cvpr2026.txt` | read; 3D-guided mask matching / depth consistency |
| Mosaic3D | NVIDIA research / CVPR 2025 | `pdfs/mosaic3d_arxiv.pdf` | `texts/mosaic3d_arxiv.txt` | skimmed for training/foundation-model trend |
| OpenTrack3D | https://arxiv.org/abs/2512.03532 | `pdfs/opentrack3d_arxiv.pdf` | `texts/opentrack3d_arxiv.txt` | read; mesh-free tracker + MLLM preprint pressure |
| SpaCeFormer | arXiv 2026 | `pdfs/spaceformer_arxiv.pdf` | `texts/spaceformer_arxiv.txt` | skimmed for efficiency/proposal-free trend |

Notes:
- `pdfs/ov3d_cg_arxiv.pdf` / `texts/ov3d_cg_arxiv.txt` is an accidental unrelated arXiv pull and is excluded from analysis.
- Review synthesis lives in `docs/ccfb_sota_critical_review_20260628.md`, `analysis/literature/ccfb_sota_20260628/online_mapping_notes.md`, `analysis/literature/ccfb_sota_20260628/ov3dis_geometry_notes.md`, and `docs/ccfb_literature_integration_20260628.md`.
