# Guideline sources and encodings

The sources below distinguish the clinical frameworks from the integer codes used in the study analysis tables. Higher stored codes indicate greater concern. The original codes remain unchanged in the primary analysis.

| Framework | Source and edition | Raw analysis codes | Common three-tier mapping |
| --- | --- | --- | --- |
| RANZCOG | *Intrapartum Fetal Surveillance*, C-Obs 1, version 5.2, June 2026 | 1, 2, 3, 4 | 1→1; 2→2; 3→2; 4→3 |
| NICHD | Macones et al., 2008 workshop report | 0, 1, 2 | 0→1; 1→2; 2→3 |
| NICE/RCOG | NICE, *Fetal monitoring in labour*, NG229; published 14 December 2022; last updated 25 March 2026 | 1, 2, 3 | 1→1; 2→2; 3→3 |
| Parer–Ikeda | Parer and Ikeda, 2007 five-tier framework | 1, 2, 3, 4, 5 | 1→1; 2→1; 3→2; 4→3; 5→3 |
| FIGO | Ayres-de-Campos et al., 2015 consensus guideline | 1, 2, 3 | 1→1; 2→2; 3→3 |

Common tiers are low (1), intermediate (2) and high (3). These mappings agree with Supplementary Table S1 and the study GPT-5.4 analysis scripts. They are fixed mappings, not outcome-dependent adjustments.

## Version and interpretation notes

RANZCOG v5.2 describes CTG features in groups relating to the likelihood of fetal compromise; the stored integers are study encodings rather than official numeric labels. The public parser therefore accepts the documented integers and does not guess a code from a risk phrase.

NICHD clinical Categories I, II and III correspond to stored codes 0, 1 and 2. Category III requires the specified combination of absent variability and recurrent decelerations or bradycardia, or a sinusoidal pattern. The intermediate category covers patterns outside I and III. A numeric response is not interpreted as a Roman-numeral category.

The current NICE NG229 document identifies 25 March 2026 as its last update. The relevant November 2025 amendment to recommendation 1.4.24 classifies late decelerations as a red feature regardless of duration or repetition. The March 2026 changes concern recording during intermittent auscultation. The repository follows this edition; `NICE/RCOG` is retained as the study display name and `rcog_label` as the existing input field. NG229 is a NICE guideline, rather than a separately versioned joint RCOG publication.

FIGO 2015 uses normal, suspicious and pathological classes. Its duration-dependent criteria remain distinct from NICE. Parer–Ikeda retains five ordered levels; it is collapsed only through the explicit S1 mapping. The Parer–Ikeda prompt references the original five-tier framework; its complete classification matrix remains in the source publication.

## References

1. Royal Australian and New Zealand College of Obstetricians and Gynaecologists. *Intrapartum Fetal Surveillance (C-Obs 1)*. Version 5.2, June 2026. [Official guideline](https://ranzcog.edu.au/wp-content/uploads/Intrapartum-Fetal-Surveillance.pdf).
2. Macones GA, Hankins GD, Spong CY, Hauth J, Moore T. The 2008 National Institute of Child Health and Human Development workshop report on electronic fetal monitoring: update on definitions, interpretation, and research guidelines. *Obstet Gynecol*. 2008;112:661–666. [doi:10.1097/AOG.0b013e3181841395](https://doi.org/10.1097/AOG.0b013e3181841395). [Co-published full text](https://onlinelibrary.wiley.com/doi/full/10.1111/j.1552-6909.2008.00284.x).
3. National Institute for Health and Care Excellence. *Fetal monitoring in labour*. NICE guideline NG229. Published 14 December 2022; last updated 25 March 2026. [Official guideline](https://www.nice.org.uk/guidance/ng229).
4. Parer JT, Ikeda T. A framework for standardized management of intrapartum fetal heart rate patterns. *Am J Obstet Gynecol*. 2007;197:26.e1–26.e6. [doi:10.1016/j.ajog.2007.03.037](https://doi.org/10.1016/j.ajog.2007.03.037).
5. Ayres-de-Campos D, Spong CY, Chandraharan E, FIGO Intrapartum Fetal Monitoring Expert Consensus Panel. FIGO consensus guidelines on intrapartum fetal monitoring: Cardiotocography. *Int J Gynaecol Obstet*. 2015;131:13–24. [doi:10.1016/j.ijgo.2015.06.020](https://doi.org/10.1016/j.ijgo.2015.06.020).

Source review date: 10 November 2026. References identify the framework editions; the retained inference records identify the historical study configuration. Copyright in guideline publications remains with the respective rights holders.
