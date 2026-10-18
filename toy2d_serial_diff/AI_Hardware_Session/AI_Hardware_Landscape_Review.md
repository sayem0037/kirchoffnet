# The AI Hardware Landscape: A Review of Publications, Patents, and Industry to Date

**A bibliometric, intellectual-property, and commercial survey of hardware for machine learning**

*Companion to "Hardware for Machine Learning." Version 1.0 — August 2026*

---

## Abstract

Where the companion paper explained *how* AI hardware works, this review maps *who has done what*. It surveys three intertwined records of the field's activity: the **academic literature** that defined its ideas, the **patent filings** that stake commercial claims over them, and the **industry** that is turning them into products worth hundreds of billions of dollars. We trace the explosive growth of publications across the venues where AI-hardware research lives (ISSCC, ISCA, MICRO, HPCA, and the pages of *Nature* and *Science*), identify the seminal and most-cited works that anchor each sub-field, and characterize the thematic shift from training accelerators toward inference, in-memory, and analog computing. On the intellectual-property side, we document a patent surge so steep that more AI-related patents were published in 2024–2025 than in the entire preceding decade, and we rank the leading assignees. On the commercial side, we chart an accelerator market of roughly \$20 billion in 2025 growing toward \$100 billion-plus by the mid-2030s, still dominated by one company holding an estimated 80–90% revenue share, but increasingly contested by hyperscaler in-house silicon and a well-funded wave of startups — one of which, Cerebras, staged the field's first blockbuster IPO, while another, Groq, saw its technology absorbed in a roughly \$20 billion transaction. We close by cross-analyzing the three records, showing where academia, patents, and products diverge — most sharply around analog and physics-based computing, where the science is rich but commercialization is nascent — and where that divergence signals opportunity. A note on method and citation integrity is included, because a landscape review is only as trustworthy as its references.

---

## Table of Contents

1. Introduction, scope, and method
2. The academic publication landscape
3. The patent landscape
4. The industry landscape
5. Cross-analysis: where the three records agree and diverge
6. Gaps, white space, and where analog fits
7. Conclusion
8. A note on citation integrity
9. References

---

## 1. Introduction, scope, and method

A field can be read three ways. Its **publications** record what its researchers believe is true and interesting. Its **patents** record what its companies believe is valuable and defensible. Its **products and funding** record what the market believes is buildable and profitable. These three records rarely tell the same story at the same time — ideas are published years before they are patented, and patented years before they ship, and some of the most-cited ideas never ship at all. Reading the three together, and paying attention to where they disagree, is the most reliable way to understand where a technology actually stands and where it is going.

This review applies that method to hardware for machine learning. The scope is deliberately broad — digital and analog, training and inference, incumbents and startups, silicon that exists and silicon that is still a research demonstration — but the treatment is a *landscape*, not an encyclopedia. We aim to give an accurate map of the territory, its major landmarks, and its contested borders, with enough specific figures and named works that a researcher can orient quickly and follow the citations to primary sources.

A word on method is owed up front. The publication and patent figures below are drawn from bibliometric databases, patent-analytics firms (IFI CLAIMS, WIPO, GreyB, PatentPC), and market-research houses. These sources are useful but not infallible: market-size forecasts in particular vary widely between firms and should be read as order-of-magnitude indicators, not precise measurements. Where a figure matters, we attribute it. Where sources disagree, we say so. And because AI-generated reviews are now a documented vector for fabricated citations — a real, resolvable DOI paired with an invented title (Topaz et al., *Lancet* 2026) — every scholarly reference in Section 9 was cross-checked against its publisher record; Section 8 explains exactly how, and where the limits of that verification lie.

---

## 2. The academic publication landscape

### 2.1 A field that grew with deep learning

Hardware for neural networks is an old idea — analog neural circuits and systolic arrays date to the 1980s — but the modern literature is a creature of the deep-learning era. The inflection point is unmistakable in the record: after 2012, as deep networks began winning vision and speech benchmarks, the number of papers on neural-network accelerators climbed steeply, and it has not stopped. The single best-known synthesis of this early wave is Sze, Chen, Yang, and Emer's *Efficient Processing of Deep Neural Networks: A Tutorial and Survey* (Proceedings of the IEEE, 2017), which has become the standard entry point to the field and one of its most-cited works. It codified the vocabulary — dataflows, weight stationarity, the energy cost of data movement — that practitioners still use.

### 2.2 Where the work is published

AI-hardware research is unusual in spanning several distinct research communities, each with its own flagship venues, and reading the field requires knowing which community a result comes from:

- **Circuits (ISSCC, VLSI, JSSC):** the International Solid-State Circuits Conference is where working chips are first disclosed with measured silicon results. If you want to know what a real accelerator achieves in joules-per-operation, ISSCC is the primary record; its 2024 program, for instance, was read by observers as a turn toward generative-AI accelerators and compute-in-memory.
- **Computer architecture (ISCA, MICRO, HPCA, ASPLOS):** these are where accelerator *architectures* and their trade-offs are argued. Google's TPU disclosure (Jouppi et al., ISCA 2017) and MIT's Eyeriss (Chen et al., ISSCC/JSSC 2016–2017) are canonical architecture-community works.
- **Devices and materials (*Nature*, *Science*, *Nature Electronics*, IEDM):** where emerging analog and in-memory technologies — memristors, phase-change memory, photonics — are first demonstrated. The photonic-computing literature, for example, traces to Shen et al., *Deep Learning with Coherent Nanophotonic Circuits* (Nature Photonics, 2017); neuromorphic silicon to Merolla et al.'s TrueNorth (Science, 2014).
- **Machine learning (NeurIPS, ICML, ICLR):** where the algorithms that hardware must serve are defined, and increasingly where hardware-algorithm co-design ideas such as Neural ODEs (Chen et al., 2018) and KirchhoffNet (Gao et al., ICCAD 2024) originate.

### 2.3 The anchor works, by sub-field

A compact way to hold the literature in mind is to remember one or two anchor papers per sub-field. The table below lists widely-cited works that define each thread; these are not necessarily the "best" papers but the ones a newcomer will see cited most often and should read first.

| Sub-field | Anchor work | Venue / year |
|---|---|---|
| Survey / foundations | Sze, Chen, Yang, Emer — *Efficient Processing of DNNs* | Proc. IEEE, 2017 |
| Systolic training/inference ASIC | Jouppi et al. — *In-Datacenter Performance Analysis of a TPU* | ISCA, 2017 |
| Energy-efficient dataflow accelerator | Chen et al. — *Eyeriss* | ISSCC 2016 / JSSC 2017 |
| Neuromorphic (spiking) | Merolla et al. — *TrueNorth* | Science, 2014 |
| Neuromorphic with on-chip learning | Davies et al. — *Loihi* | IEEE Micro, 2018 |
| Digital near-memory inference | Modha et al. — *NorthPole* | Science, 2023 |
| Photonic computing | Shen et al. — *Coherent Nanophotonic Circuits* | Nature Photonics, 2017 |
| Continuous-depth models | Chen et al. — *Neural ODEs* | NeurIPS, 2018 |
| Physics-based analog network | Gao et al. — *KirchhoffNet* | ICCAD, 2024 |

### 2.4 What the literature is moving toward

Three thematic shifts are legible in the recent record. First, the center of gravity has moved from **training** to **inference**: as trained models proliferate, the economic weight of running them (in data centers and at the edge) now exceeds that of training them, and accelerator papers increasingly optimize for inference efficiency and low precision. Second, **compute-in-memory** has moved from a niche device-physics topic to a mainstream architecture theme, appearing prominently at both circuits and architecture venues, driven by the recognition that data movement — not arithmetic — is the binding constraint. Third, and most relevant to the companion paper, **analog and physics-based co-design** is a growing but still-small share of the literature: memristor and photonic demonstrations appear regularly in *Nature*/*Science*, and algorithm-hardware unifications like equilibrium propagation and KirchhoffNet appear at ML and EDA venues, but this work remains a research frontier rather than a mature body.

---

## 3. The patent landscape

### 3.1 A filing surge without precedent

If the publication record grew steeply, the patent record has gone nearly vertical. According to WIPO, more AI-related patents were published in 2024 and 2025 than in the entire preceding ten years combined; published generative-AI patent families alone rose from roughly 14,000 in 2023 to over 37,800 in 2025. This reflects a broad land-grab across the AI stack, of which hardware is one contested territory. The signal to extract is not the precise count — patent-family counting methods differ between analytics firms — but the slope: companies are racing to stake defensible claims faster than at any prior point in the industry's history.

### 3.2 Who holds the claims

Patent leadership must be read carefully, because "most patents overall" and "most AI-chip patents specifically" are different rankings, and raw counts reward volume filers over quality. Two lenses:

**Overall US patent grants (2024).** Samsung led with roughly 6,377 granted patents (nearly 2% of all US grants), followed by TSMC with about 3,989. IBM, long the perennial leader, continued a deliberate retreat down the rankings, landing around eighth with roughly 2,465 grants, down from 3,658 in 2023.

**AI-chip patents specifically.** By analyses focused on AI accelerator and chip patents, the US leaders are IBM, Samsung, Intel, Google, and Microsoft, with IBM well out in front on cumulative holdings — a reflection of its decades of research investment in both digital accelerators and analog/neuromorphic devices. Notably, NVIDIA — the commercial leader by a wide margin — does **not** top the AI-chip patent counts; analyses characterize its strategy as quality over quantity, filing fewer but strategically central patents rather than maximizing volume.

| Lens | Leaders (approximate order) | Notable point |
|---|---|---|
| All US grants, 2024 | Samsung, TSMC, … IBM (~8th) | Volume dominated by foundry/manufacturer filers |
| AI-chip patents (cumulative) | IBM, Samsung, Intel, Google, Microsoft | IBM well ahead; reflects long research base |
| Generative-AI patent families | SoftBank, Tencent, Ping An, Baidu, + Alphabet/Microsoft/IBM | Asia-heavy; US giants in top ten |
| Commercial leader vs. patent leader | NVIDIA leads market, not patent counts | "Quality not quantity" filing strategy |

### 3.3 Geography and the read-across

The patent record is strikingly bipolar between the United States and China, with China's filers dominating raw generative-AI application volume and US firms concentrating on foundational and hardware claims. The strategic read-across for hardware is twofold. First, the incumbents' patent portfolios are broad enough that a new entrant must design around a dense thicket, particularly in GPU-style architectures and memory interfaces. Second — and this is the opening — the analog, photonic, and physics-based corners of the field are comparatively less crowded with patents than the digital core, because the underlying science is younger. For a research group producing genuinely novel analog IP (a KirchhoffNet-style circuit, for instance), the patent white space is wider than in the digital mainstream, though so is the distance to a product.

---

## 4. The industry landscape

### 4.1 Market size and the shape of the money

The AI-accelerator market was on the order of **\$20–21 billion in 2025** by several market-research estimates, with forecasts converging on roughly **\$100 billion-plus by the early-to-mid 2030s** at compound annual growth rates in the high teens to low twenties percent. These figures should be treated as directional — different firms draw the category boundary differently (data-center GPUs only, versus all accelerators including edge NPUs) and their absolute numbers vary by a factor of two or more — but the qualitative story is unambiguous: this is one of the fastest-growing hardware markets in history, and the growth is driven by data-center demand for generative-AI training and inference.

### 4.2 The incumbent: one company, most of the market

The defining fact of the current industry is **NVIDIA's dominance**. Estimates place its share of the AI-accelerator market at roughly **80–90% by revenue** as of 2025, with data-center revenue reported to be on the order of \$100 billion-plus annually and projected higher still. This dominance rests not only on its GPUs but on **CUDA** — the software ecosystem that makes its hardware the path of least resistance for every ML researcher — which is the single largest barrier any competitor faces. The consensus expectation is that NVIDIA's *share* will erode gradually (toward perhaps 75% by 2026 in some estimates) even as its absolute revenue grows, as custom silicon and rivals scale. AMD (with its Instinct GPUs) and Intel (with the Gaudi line) are the principal merchant challengers, but neither has yet meaningfully dented the ecosystem lock-in.

### 4.3 The hyperscalers: buyers becoming builders

The most structurally important trend is that NVIDIA's largest customers are becoming its competitors. The major cloud providers have each built in-house AI silicon to reduce dependence and cost:

- **Google** — the TPU line, the longest-running hyperscaler program, now in volume deployment (v6 "Trillium") with successor generations ramping.
- **Amazon** — Trainium (training) and Inferentia (inference), with Trainium 2 in volume production and later generations sampling.
- **Microsoft** — the Maia accelerator, serving large-model workloads including those of its partner OpenAI.
- **Meta** — MTIA, its in-house inference silicon, now in its volume generation.

Collectively, hyperscaler custom accelerators are being deployed at a scale of on the order of a million-plus units per year, and this in-house silicon — much of it designed in partnership with Broadcom and Marvell — is the most credible medium-term check on NVIDIA's share. Strategically, it validates the companion paper's point that when you control both the workload and the wallet, a specialized ASIC accelerating a stable primitive (the MVM) beats a general-purpose part on cost.

### 4.4 The startups: a well-funded insurgency

Beyond the incumbents and hyperscalers sits a large cohort of venture-funded challengers, collectively having raised well over ten billion dollars, betting that novel architectures can beat the GPU on specific axes — usually inference latency, cost, or energy. The period from late 2025 into 2026 was the sector's most active yet, marked by two watershed events: **Cerebras** — maker of wafer-scale engines — became the field's first blockbuster IPO, opening far above its expected range at a multi-tens-of-billions valuation; and **Groq**, whose deterministic "language processing unit" targets low-latency inference, saw its technology licensed to NVIDIA in a transaction reported at roughly \$20 billion, the defining consolidation event of the independent-chip era.

| Company | Architecture bet | Status / signal |
|---|---|---|
| Cerebras | Wafer-scale engine (one giant chip) | First AI-chip IPO of the cycle; multi-\$10B valuation |
| Groq | Deterministic LPU for low-latency inference | Technology licensed to NVIDIA (~\$20B deal) |
| SambaNova | Reconfigurable dataflow | Enterprise/inference focus |
| Graphcore | IPU (graph/parallel) | Acquired by SoftBank |
| Tenstorrent | RISC-V + AI (Jim Keller) | Multiple funding rounds |
| Etched | Transformer-only ASIC ("Sohu") | ~\$10B valuation on transformer bet |
| d-Matrix | Digital in-memory compute | Microsoft-backed; ~\$2B valuation |
| Lightmatter | Photonic compute/interconnect | ~\$4.4B valuation, \$400M Series D |
| Mythic, BrainChip | Analog CIM / neuromorphic edge | Edge inference niches |

The insurgency's structural challenge is the same for all of them: hardware advantages are necessary but not sufficient against CUDA. The startups that have gained the most traction are those that either target a workload the GPU serves poorly (ultra-low-latency inference, wafer-scale single-model throughput) or that abstract their hardware behind familiar software.

### 4.5 The analog, photonic, and neuromorphic frontier in industry

The emerging-hardware families that dominate the *research* record occupy a much smaller commercial footprint, and honestly assessing that gap matters. **Photonics** has the most conspicuous commercial momentum: Lightmatter reached a roughly \$4.4 billion valuation in late 2024 on a \$400 million round, positioning photonic technology as much for chip-to-chip interconnect (a nearer-term need) as for computation itself. **Analog compute-in-memory** has several venture entrants (d-Matrix, Mythic) and deep incumbent research (IBM's analog AI chips using phase-change memory, distinct from its digital NorthPole), but no analog accelerator yet holds meaningful data-center market share. **Neuromorphic** computing remains largely a research-and-defense endeavor (Intel's Loihi, IBM's TrueNorth lineage, BrainChip's edge parts), with commercial traction concentrated in niche low-power sensing rather than mainstream AI. The pattern is consistent: analog and physics-based approaches are richly represented in publications, thinly represented in products, and that gap is the field's central unresolved question.

---

## 5. Cross-analysis: where the three records agree and diverge

Laying the three records side by side reveals the field's real structure more clearly than any one of them alone.

**They agree that the memory wall is the organizing problem.** Publications optimize dataflow to minimize data movement; patents cluster around memory interfaces and in-memory compute; products (from TPUs to NorthPole to crossbar startups) compete on keeping weights near compute. On this, science, IP, and industry are aligned.

**They diverge sharply on analog.** This is the most informative disagreement in the field. The *publication* record treats analog and physics-based computing as a major and growing frontier — memristor and photonic papers are prestige results in *Nature* and *Science*. The *patent* record shows analog as comparatively open white space. But the *product* record shows analog as barely commercialized, with the partial exception of photonics-for-interconnect. This three-way divergence is the signature of a technology that is scientifically validated, legally unclaimed, and commercially unproven — precisely the profile of a high-risk, high-reward opportunity. It is exactly where a physics-based approach like KirchhoffNet lives.

**They diverge on who leads.** The commercial leader (NVIDIA) is not the patent leader (IBM/Samsung) and is not always the publication leader (academia and Google/IBM research). Dominance in one record does not transfer automatically to the others — a reminder that market position rests on ecosystem and execution as much as on invention.

**They agree that specialization is ascendant.** The end of easy scaling shows up in all three records as a move from general-purpose to specialized: architecture papers on domain-specific accelerators, patents on workload-specific datapaths, and the hyperscalers' pivot to custom silicon. The strategic caveat, visible in the product record, is that over-specialization is dangerous when the workload moves — the reason the most durable bets accelerate the stable MVM primitive rather than a specific model.

---

## 6. Gaps, white space, and where analog fits

Reading across the landscape, several opportunities stand out for a researcher or team deciding where to invest.

The clearest white space is **analog and physics-based inference with an honest accuracy story**. The science exists, the patents are sparse, and no product dominates — but the reason is the unsolved problem the companion paper detailed: analog non-idealities (drift, variation, noise, ADC overhead) erode the efficiency advantage by an uncertain amount. Whoever converts a laboratory analog demonstration into a manufacturable system with a quantified, tolerable accuracy loss captures a genuinely open field. This is not a niche observation; it is the single largest gap between what the literature promises and what the market has.

A second opportunity is **software and mapping for non-GPU hardware**. The consistent lesson of the industry record is that the most efficient hardware does not win — the most usable hardware wins. A compiler stack that lets novel silicon accept mainstream models with minimal friction is worth as much as the silicon itself, and is comparatively under-invested relative to the hardware.

A third is **interconnect and system-level integration**, where photonics has already found its nearest-term commercial foothold. As models outgrow single chips, the bottleneck moves from the accelerator to the fabric connecting many accelerators, and this system-level problem is where several well-funded companies are now concentrating.

Within this map, a **KirchhoffNet-style approach** occupies a specific and defensible position: it is analog (efficiency frontier), physics-based (patent white space), inference-oriented (the growing market), and co-designed (the research frontier). Its risk is equally specific and is shared with the whole analog frontier — it must prove end-to-end efficiency and accuracy in real silicon, not just in simulation, and scale past toy problems. The landscape does not tell us whether it will succeed; it tells us that the space it targets is real, under-claimed, and unproven, which is the most that any map can honestly offer.

---

## 7. Conclusion

The three records of AI hardware — publications, patents, and products — tell a coherent story when read together. A field that was a research curiosity before 2012 has become one of the fastest-growing hardware markets in history, its literature expanding across four research communities, its patents surging past all historical precedent, and its commercial value concentrated in a single dominant firm now being challenged from two directions: its own largest customers building in-house silicon, and a well-capitalized wave of architectural insurgents. Beneath the digital mainstream that runs today's AI sits an analog and physics-based frontier that is scientifically rich, legally open, and commercially unproven — the field's defining tension and its largest opportunity. For a researcher entering now, the map's most actionable feature is the divergence between what the literature celebrates and what the market has shipped: that gap, most conspicuous around analog computing, is where the unclaimed territory lies.

---

## 8. A note on citation integrity

Because AI-assisted reviews are a documented source of fabricated references — the well-characterized failure mode being a real, resolvable identifier attached to an invented or mismatched title (Topaz et al., *Lancet*, 2026) — the scholarly citations in Section 9 were treated with corresponding care. Each peer-reviewed reference's DOI or arXiv identifier and its title were cross-checked against publisher and preprint records (IEEE Xplore, ACM Digital Library, *Science*/*Nature*, and arXiv) during research. A dedicated citation-verification service (which compares a claimed title against the record its identifier actually resolves to, catching the mismatch pattern that simple "does the DOI load?" checks miss) was attempted but was unavailable in this environment due to access restrictions; the manual cross-check is therefore the basis of the verification, and readers requiring formal integrity assurance should re-run the reference list through such a tool. The industry, market, and patent figures throughout are drawn from analytics and market-research sources named inline; these are inherently estimative, vary between providers, and are presented as directional rather than exact. Where this review states a number, it has tried to state its provenance.

---

## 9. References

**Peer-reviewed / preprint (identifiers cross-checked against publisher records):**

1. V. Sze, Y.-H. Chen, T.-J. Yang, J. S. Emer. *Efficient Processing of Deep Neural Networks: A Tutorial and Survey.* Proceedings of the IEEE, 105(12), 2295–2329, 2017. DOI: 10.1109/JPROC.2017.2761740
2. N. P. Jouppi et al. *In-Datacenter Performance Analysis of a Tensor Processing Unit.* ISCA 2017. DOI: 10.1145/3079856.3080246
3. Y.-H. Chen, T. Krishna, J. S. Emer, V. Sze. *Eyeriss: An Energy-Efficient Reconfigurable Accelerator for Deep Convolutional Neural Networks.* IEEE JSSC, 52(1), 127–138, 2017. DOI: 10.1109/JSSC.2016.2616357
4. P. A. Merolla et al. *A million spiking-neuron integrated circuit with a scalable communication network and interface (TrueNorth).* Science, 345(6197), 668–673, 2014. DOI: 10.1126/science.1254642
5. M. Davies et al. *Loihi: A Neuromorphic Manycore Processor with On-Chip Learning.* IEEE Micro, 38(1), 82–99, 2018. DOI: 10.1109/MM.2018.112130359
6. D. S. Modha et al. *Neural inference at the frontier of energy, space, and time (NorthPole).* Science, 382(6668), 329–335, 2023. DOI: 10.1126/science.adh1174
7. Y. Shen et al. *Deep Learning with Coherent Nanophotonic Circuits.* Nature Photonics, 11, 441–446, 2017. DOI: 10.1038/nphoton.2017.93
8. R. T. Q. Chen, Y. Rubanova, J. Bettencourt, D. Duvenaud. *Neural Ordinary Differential Equations.* NeurIPS 2018. arXiv:1806.07366
9. Z. Gao, F.-K. Sun, R. Rohrer, D. S. Boning. *KirchhoffNet: A Scalable Ultra Fast Analog Neural Network.* ICCAD 2024. arXiv:2310.15872; DOI: 10.1145/3676536.3676662

**Industry, patent, and market sources (estimative; cited inline):**

10. WIPO. *Patent Landscape Report: Generative Artificial Intelligence (GenAI)*, and 2026 press briefing on GenAI patent growth. wipo.int
11. IFI CLAIMS Patent Services. *2024 Trends & Insights / US Patent Rankings.* ificlaims.com
12. GreyB and PatentPC. *Artificial Intelligence / AI Hardware Patent Landscape analyses.* insights.greyb.com; patentpc.com
13. Digital Science. *Nvidia Goes for Quality, Not Quantity, in AI Chip Patents.* digital-science.com
14. Mordor Intelligence; MarketsandMarkets; Precedence Research; Fortune Business Insights. *AI Accelerator / Data-Center GPU market size and forecast reports, 2025.*
15. EE Times. *Cerebras IPO Revives AI Chip Startup Fever.* eetimes.com
16. Lightmatter. *Series D press release — \$400M, \$4.4B valuation* (Oct 2024); Bloomberg coverage.
17. Tom's Hardware; Spheron. *Hyperscaler custom AI silicon coverage — Google TPU, AWS Trainium, Microsoft Maia, Meta MTIA (2024–2026).*
18. IBM Research. *NorthPole and the AIU analog/near-memory chip family.* research.ibm.com
19. B. Reuther et al. *AI Accelerator Survey and Benchmarking* (MIT Lincoln Laboratory, IEEE HPEC series) — for cross-vendor accelerator comparison.
20. M. C. Topaz et al. *On fabricated citations in AI-generated text.* Lancet, 2026 (cited for the citation-integrity failure mode).

---

*Companion to "Hardware for Machine Learning: A Practical Review of Digital and Analog AI Accelerators." Bibliometric and market figures are directional and attributed inline; scholarly identifiers were manually cross-checked against publisher records (see Section 8).*
