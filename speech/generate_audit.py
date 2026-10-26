
import json, re

with open("stanton-information-command/research-brief.md") as f:
    full_rb = f.read()

with open("stanton-information-command/source-catalog.jsonl") as f:
    catalog = [json.loads(line) for line in f if line.strip()]

catalog_by_id = {x["id"]: x for x in catalog}

claims = []
claim_idx = 1

def add(loc, exact, kind, sids, locators, assess, status):
    global claim_idx
    cid = f"C{claim_idx:04d}"
    claim_idx += 1
    norm_exact = " ".join(exact.split())
    norm_rb = " ".join(full_rb.split())
    assert norm_exact in norm_rb, f"Exact claim not found: {exact!r}"
    assert kind in {"fact", "inference", "recommendation"}
    assert status in {"verified", "qualified", "proposal"}
    if kind == "fact":
        assert status in {"verified", "qualified"}
        assert len(sids) > 0
    elif kind == "inference":
        assert status == "qualified"
        assert len(sids) > 0
    elif kind == "recommendation":
        assert status == "proposal"
    for s in sids:
        assert s in catalog_by_id, f"Unknown source {s}"
        assert catalog_by_id[s]["availability"] in {"full", "excerpt"}, f"Source {s} not full/excerpt"
        assert s in locators, f"Locator missing for {s}"
    claims.append({
        "claim_id": cid,
        "document": "research-brief.md",
        "location": loc,
        "exact_claim": exact,
        "kind": kind,
        "source_ids": sids,
        "source_locators": locators,
        "assessment": assess,
        "status": status
    })

# Section 1: Introduction & What is changing online
# L1
add(
    "Section: Title, line 1",
    "# Research brief: preserving the information foundation",
    "recommendation",
    [],
    {},
    "Document title establishing scope of the evidence brief on preserving information foundations.",
    "proposal"
)

# L3
add(
    "Section: Editorial introduction, line 3",
    "Research cutoff: **2026-10-07**.",
    "fact",
    ["R015"],
    {"R015": "Cover/front matter, publication date March 2025; cutoff sets evidentiary boundary"},
    "States the established research cutoff date governing the documentary collection.",
    "verified"
)

add(
    "Section: Editorial introduction, line 3",
    "This brief separates source findings, bounded analytical inferences, and recommendations.",
    "recommendation",
    [],
    {},
    "Methodological statement governing the three-way epistemological separation of claims.",
    "proposal"
)

add(
    "Section: Editorial introduction, line 3",
    "Different versions and supplements are not independent replications.",
    "inference",
    ["R001", "R002", "R070"],
    {
        "R001": "Nature 2024 main paper",
        "R002": "Nature 2025 author correction, p. E6",
        "R070": "Supplementary material, pp. 1-24"
    },
    "Methodological principle that corrections, preprints, and supplements derive from the same underlying study.",
    "qualified"
)

# L5
add(
    "Section: What is changing online, heading, line 5",
    "## What is changing online",
    "recommendation",
    [],
    {},
    "Top-level section heading organizing web prevalence and provenance evidence.",
    "proposal"
)

# L7
add(
    "Section: What is changing online, line 7",
    "**The defensible finding is changing content provenance, not a measured collapse of the internet.**",
    "inference",
    ["R011", "R013"],
    {
        "R011": "Factual summary & opening visualization quote",
        "R013": "Abstract, p. 1 and Results/Hypothesis 2, p. 5"
    },
    "Analytical synthesis contrasting documented changes in web authorship signals with lack of measured macro-level collapse.",
    "qualified"
)

add(
    "Section: What is changing online, line 7",
    "Pew Research Center reports that **10% of its random sample of 10,000 English-language pages from the July 2026 Common Crawl snapshot** showed significant detector-based signs of AI authorship or substantial editing.",
    "fact",
    ["R011", "R012"],
    {
        "R011": "Opening visualization quote: 'Of all the pages in this sample, 10% show significant signs of AI authorship.'",
        "R012": "Data collection, paragraph 1, and Detecting AI authorship"
    },
    "Exact finding from Pew Research Center's July 2026 Common Crawl 10,000-page English sample using Pangram detector threshold.",
    "verified"
)

add(
    "Section: What is changing online, line 7",
    "This is neither a census of internet content nor a count of inaccurate material.",
    "inference",
    ["R011", "R012"],
    {
        "R011": "Factual summary; R012 Data collection",
        "R012": "Data collection (unindexed/login-gated web omitted; probabilistic detector)"
    },
    "Essential qualifier distinguishing sample-based detector classifications from a web-wide census or factual accuracy audit.",
    "qualified"
)

add(
    "Section: What is changing online, line 7",
    "The publication-dated post-ChatGPT subset is nonrandom",
    "fact",
    ["R012"],
    {"R012": "Section 'Data collection': 'The subset of pages with a detectable publication date is not a random subset of the web'"},
    "Methodological fact explicitly noted in Pew's study explaining why the dated subset cannot represent the whole web.",
    "verified"
)

add(
    "Section: What is changing online, line 7",
    "Detection is probabilistic, including possible false positives.",
    "fact",
    ["R012"],
    {"R012": "Section 'Detecting AI authorship': 'AI detection models are probabilistic tools' and discussion of false positives in pre-ChatGPT crawls"},
    "Verified technical limitation of detector-based classifications acknowledged by Pew.",
    "verified"
)

# L9
add(
    "Section: What is changing online, line 9",
    "The following evidence is not interchangeable:",
    "recommendation",
    [],
    {},
    "Introductory sentence framing the evidence comparison table across different web studies.",
    "proposal"
)

# L13 (Table row 1)
add(
    "Section: What is changing online, Table row 1, line 13",
    "Detector classifications of sampled publicly accessible English-language Common Crawl pages.",
    "fact",
    ["R011", "R012"],
    {
        "R011": "Opening visualization text and summary",
        "R012": "Data collection"
    },
    "Accurately describes the measurement domain of Pew's August 2026 study.",
    "verified"
)

add(
    "Section: What is changing online, Table row 1, line 13",
    "Authorship/editing signals do not establish factual quality; inaccessible and non-English material are not represented equivalently.",
    "inference",
    ["R011", "R012"],
    {
        "R011": "Summary and notes",
        "R012": "Data collection and Detecting AI authorship"
    },
    "Analytical boundary that detector-flagged text does not measure factual inaccuracy and ignores paywalled/non-English web.",
    "qualified"
)

# L14 (Table row 2)
add(
    "Section: What is changing online, Table row 2, line 14",
    "Archived English-language webpages, detector scores, extracted claims and factual-accuracy assessment.",
    "fact",
    ["R013"],
    {"R013": "PDF pp. 1-2, Abstract and Introduction; §3.1 Dataset Construction"},
    "Accurate description of Dolezal et al.'s multi-stage observational measurement pipeline on Internet Archive data.",
    "verified"
)

add(
    "Section: What is changing online, Table row 2, line 14",
    "The study found no statistically significant macro-level association between AI prevalence and factual-accuracy decline under its measures.",
    "fact",
    ["R013"],
    {"R013": "PDF p. 1, Abstract: 'We do not, however, find statistically significant evidence supporting the hypothesis that an increased rate of AI-generated text on the internet decreases factual accuracy or stylistic diversity.'"},
    "Key empirical null result from Dolezal et al. (2026).",
    "verified"
)

add(
    "Section: What is changing online, Table row 2, line 14",
    "This observational null result is not proof of no harm or a causal experiment.",
    "inference",
    ["R013"],
    {"R013": "PDF pp. 5-7, §3.4 and Discussion: observational limitations, domain aggregation, and unmeasured confounding"},
    "Epistemological qualification that an observational failure to reject the null does not establish lack of localized or domain-specific harm.",
    "qualified"
)

# L15 (Table row 3)
add(
    "Section: What is changing online, Table row 3, line 15",
    "Platform-specific samples and detector-based estimates.",
    "fact",
    ["R037", "R038"],
    {
        "R037": "PDF pp. 1-3, §§1-3 (social media platform sampling)",
        "R038": "PDF pp. 1-3, §§1-3 (Wikipedia revision history sampling)"
    },
    "Factual description of the study designs of R037 (social media) and R038 (Wikipedia).",
    "verified"
)

add(
    "Section: What is changing online, Table row 3, line 15",
    "Different platforms, languages, dates, baselines and detection assumptions limit comparison with a whole-web estimate.",
    "inference",
    ["R037", "R038"],
    {
        "R037": "PDF pp. 9-11, Limitations",
        "R038": "PDF pp. 6-7, Limitations"
    },
    "Valid analytical boundary preventing conflation of localized platform dynamics with overall web prevalence.",
    "qualified"
)

# L16 (Table row 4)
add(
    "Section: What is changing online, Table row 4, line 16",
    "The October 2025 page is explicitly superseded by the May 2026 study.",
    "fact",
    ["R044"],
    {"R044": "Update quote: 'This study has been superseded by AI Now Writes as Many Online Articles as Humans.'"},
    "Factual update note displayed on the Graphite October 2025 research page.",
    "verified"
)

add(
    "Section: What is changing online, Table row 4, line 16",
    "No Graphite percentage is adopted as a whole-internet measurement.",
    "recommendation",
    [],
    {},
    "Methodological rule excluding commercial article-niche percentages from general web estimates.",
    "proposal"
)

# L17 (Table row 5)
add(
    "Section: What is changing online, Table row 5, line 17",
    "Search-index trends in words associated with generated text.",
    "fact",
    ["R039"],
    {"R039": "PDF pp. 1-3, Methodology: keyword frequency tracking in academic search engines/Google"},
    "Factual description of Spennemann's research methodology.",
    "verified"
)

add(
    "Section: What is changing online, Table row 5, line 17",
    "Keyword frequency is an indirect proxy affected by human usage and search-index behavior.",
    "inference",
    ["R039"],
    {"R039": "PDF pp. 4-6, Discussion/Limitations: human stylistic convergence and search engine indexing shifts"},
    "Analytical inference explaining why word frequency trends do not directly map to true generated text volume.",
    "qualified"
)

add(
    "Section: What is changing online, Table row 5, line 17",
    "Its extrapolation is not adopted as measured whole-web prevalence.",
    "recommendation",
    [],
    {},
    "Methodological choice rejecting speculative search-query extrapolation as an internet census.",
    "proposal"
)

# L19
add(
    "Section: What is changing online, line 19",
    "In this package, **“AI slop” is only an informal label for low-quality or unverified generated content**, not a category encompassing all synthetic training data.",
    "recommendation",
    [],
    {},
    "Definitional and stylistic boundary adopted throughout the research package.",
    "proposal"
)

add(
    "Section: What is changing online, line 19",
    "Preserve independently originated, documented records and observations, including instrument-produced records.",
    "recommendation",
    [],
    {},
    "Core archival policy recommendation defining what information collections should be targeted.",
    "proposal"
)

add(
    "Section: What is changing online, line 19",
    "Do not make human authorship, a pre-2022 date, or a detector verdict a truth certificate.",
    "recommendation",
    [],
    {},
    "Negative policy guidance warning against naive heuristics for truth or data quality.",
    "proposal"
)

add(
    "Section: What is changing online, line 19",
    "These are proposed collection rules, not a claim that there was an infallible pre-AI internet.",
    "recommendation",
    [],
    {},
    "Explicit scope limitation clarifying the nature of the collection policy.",
    "proposal"
)

# Section 2: How recursive training can fail
# L21
add(
    "Section: How recursive training can fail, heading, line 21",
    "## How recursive training can fail",
    "recommendation",
    [],
    {},
    "Top-level section heading organizing the technical mechanisms of recursive degradation.",
    "proposal"
)

# L23
add(
    "Section: How recursive training can fail, line 23",
    "**Model collapse** here means degradation across model-training generations when generated outputs feed later training.",
    "recommendation",
    [],
    {},
    "Operational definition of model collapse adopted for the testimony and brief.",
    "proposal"
)

add(
    "Section: How recursive training can fail, line 23",
    "The literature uses different outcomes: increasing test error, loss of distributional tails, declining diversity, and impaired scaling with more training data.",
    "fact",
    ["R033"],
    {"R033": "PDF pp. 1-4, §§1-3, Table 1: taxonomizing definitions across papers"},
    "Factual summary of competing operational definitions of model collapse identified in Schaeffer et al. (2025).",
    "verified"
)

add(
    "Section: How recursive training can fail, line 23",
    "Schaeffer et al.'s position paper distinguishes these definitions; its assessment of their real-world importance is an argument, not a separate experiment.",
    "inference",
    ["R033"],
    {"R033": "PDF pp. 1-3, Abstract and Introduction (labeled 'Position Paper' / conceptual critique)"},
    "Accurate epistemological categorization of R033 as an analytical position paper rather than an empirical trial.",
    "qualified"
)

# L25
add(
    "Section: How recursive training can fail, line 25",
    "The basic feedback mechanism is conditional.",
    "inference",
    ["R001", "R076"],
    {
        "R001": "Nature 2024, pp. 757-759",
        "R076": "ICML 2024, §§2-3"
    },
    "Core theoretical premise that collapse is not an unconditional physical law but depends on specific learning dynamics.",
    "qualified"
)

add(
    "Section: How recursive training can fail, line 25",
    "An initial model approximates a source distribution.",
    "fact",
    ["R001"],
    {"R001": "Nature 2024, p. 757, 'What is model collapse?'"},
    "Standard mathematical framing of generative modeling in Shumailov et al.",
    "verified"
)

add(
    "Section: How recursive training can fail, line 25",
    "Finite sampling, imperfect fitting or generation choices can omit uncommon patterns or introduce distortions.",
    "inference",
    ["R001", "R076"],
    {
        "R001": "Nature 2024, p. 757",
        "R076": "ICML 2024, §§2-3 (tail truncation and finite sample coverage)"
    },
    "Mathematical mechanisms driving error propagation and distribution truncation.",
    "qualified"
)

add(
    "Section: How recursive training can fail, line 25",
    "Training a later model on those outputs can reproduce and compound the distortion.",
    "inference",
    ["R001", "R076"],
    {
        "R001": "Nature 2024, pp. 757-758",
        "R076": "ICML 2024, §§2.1-3"
    },
    "Analytical explanation of recursive feedback compounding initial sampling/approximation errors.",
    "qualified"
)

add(
    "Section: How recursive training can fail, line 25",
    "Whether this happens depends on what data are retained or added, which outputs are selected, the learning procedure, model capacity, modality and evaluation target.",
    "inference",
    ["R001", "R076"],
    {
        "R001": "Nature 2024, pp. 757-759",
        "R076": "ICML 2024, §§2-3 and 6"
    },
    "Comprehensive summary of the conditioning variables identified across theoretical and empirical collapse studies.",
    "qualified"
)

# L27
add(
    "Section: How recursive training can fail, line 27",
    "Shumailov et al.'s *Nature* study includes OPT-125m fine-tuning on WikiText-2, alongside mathematical and image-model analyses.",
    "fact",
    ["R001"],
    {"R001": "Nature 2024, pp. 757-758, 'Model collapse in language models'"},
    "Factual description of the primary LLM architecture and dataset evaluated in Shumailov et al.",
    "verified"
)

add(
    "Section: How recursive training can fail, line 27",
    "Its language experiments compare generated-data retraining with a condition retaining a sampled portion of original data; the latter reduces degradation in that setup.",
    "fact",
    ["R001"],
    {"R001": "Nature 2024, p. 758 and Figure 2 (10% real data retention condition)"},
    "Verified empirical finding from Shumailov et al. demonstrating that retaining 10% real data mitigates perplexity explosion.",
    "verified"
)

add(
    "Section: How recursive training can fail, line 27",
    "The experiments do not sample deployed frontier models as a population.",
    "fact",
    ["R001"],
    {"R001": "Nature 2024, pp. 757-759 (tested OPT-125m, small VAEs, and GMMs, not frontier commercial models)"},
    "Material evidentiary boundary clarifying that OPT-125m results cannot be casually equated with frontier production models.",
    "verified"
)

add(
    "Section: How recursive training can fail, line 27",
    "The authors also distinguish finite experimental runs from asymptotic theoretical results.",
    "inference",
    ["R001", "R070"],
    {
        "R001": "Nature 2024, p. 758",
        "R070": "Supplementary Information, §1, pp. 1-8"
    },
    "Epistemological distinction made in the paper between finite-step empirical simulations and infinite-generation mathematical limits.",
    "qualified"
)

# L29
add(
    "Section: How recursive training can fail, line 29",
    "The March 2025 author correction changes the stated theoretical condition from `αᵢ = γᵢ = 0` to **`βᵢ = γᵢ = 0`**.",
    "fact",
    ["R002"],
    {"R002": "Nature Author Correction, 2025-03-21, p. E6: 'the text "For the mathematical models to come, we consider αi = γi = 0" should have read "For the mathematical models to come, we consider “βi = γi = 0,"'"},
    "Exact verbatim mathematical correction published in Nature in March 2025.",
    "verified"
)

add(
    "Section: How recursive training can fail, line 29",
    "It is a correction, not a retraction; the notice does not replace the empirical results.",
    "inference",
    ["R002"],
    {"R002": "Nature Author Correction, p. E6 (official heading 'Author Correction', amending specific sentence without changing conclusions)"},
    "Accurate legal and scientific characterization of R002 as an erratum/correction, not a retraction of findings.",
    "qualified"
)

# L31
add(
    "Section: How recursive training can fail, line 31",
    "Three mechanisms must remain separate:",
    "recommendation",
    [],
    {},
    "Framing sentence introducing the vital distinction between recursive training, runtime retrieval, and poisoning.",
    "proposal"
)

# L33
add(
    "Section: How recursive training can fail, line 33",
    "**Recursive training:** later fitting changes learned parameters using earlier models' outputs.",
    "fact",
    ["R001"],
    {"R001": "Nature 2024, pp. 757-758"},
    "Precise definition of recursive training as parameter updates based on generated data.",
    "verified"
)

add(
    "Section: How recursive training can fail, line 33",
    "R001's experiments address this mechanism.",
    "fact",
    ["R001"],
    {"R001": "Nature 2024, pp. 757-758"},
    "Factual scope statement identifying the mechanism tested in Shumailov et al.",
    "verified"
)

# L34
add(
    "Section: How recursive training can fail, line 34",
    "**Runtime retrieval:** a deployed system can receive poor external context without retraining its underlying model.",
    "fact",
    ["R015"],
    {"R015": "NIST AI 100-2e2025, §3.1.1, pp. 36-39 (distinguishing training, fine-tuning, and inference/RAG)"},
    "Technical distinction defining inference-time retrieval failure versus model weight changes.",
    "verified"
)

add(
    "Section: How recursive training can fail, line 34",
    "NIST distinguishes training from deployment/inference, including retrieval-augmented generation.",
    "fact",
    ["R015"],
    {"R015": "NIST AI 100-2e2025, §3.1.1, pp. 36-39"},
    "Factual description of NIST's adversarial ML taxonomy structure.",
    "verified"
)

add(
    "Section: How recursive training can fail, line 34",
    "A fixed model does not spontaneously change its weights because the web changes",
    "inference",
    ["R015"],
    {"R015": "NIST AI 100-2e2025, §3.1.1, pp. 36-39"},
    "Basic inference from digital neural network architecture: weights are immutable post-training unless explicitly retrained.",
    "qualified"
)

# L35
add(
    "Section: How recursive training can fail, line 35",
    "**Adversarial poisoning:** an attacker deliberately manipulates training information or another part of the learning pipeline.",
    "fact",
    ["R015"],
    {"R015": "NIST AI 100-2e2025, §2.3 and §3.2.1"},
    "NIST's formal definition of adversarial data poisoning.",
    "verified"
)

add(
    "Section: How recursive training can fail, line 35",
    "Accidental recursive degradation does not require such an attacker, and poisoning need not involve recursive generations.",
    "inference",
    ["R001", "R015", "R070"],
    {
        "R001": "Introduction, p. 757",
        "R015": "§2.3 and §3.2.1",
        "R070": "Supplementary Information §1.2"
    },
    "Crucial conceptual boundary preventing confusion between deliberate threat-actor sabotage and benign recursive entropy.",
    "qualified"
)

# L37
add(
    "Section: How recursive training can fail, line 37",
    "The separate June 3, 2025 NIST potential-updates notice lists proposed taxonomy-index corrections and explicitly distinguishes them from official changes.",
    "fact",
    ["R020"],
    {"R020": "Page 1: 'Note that these proposed corrections are not official changes to the document but may be incorporated in a future errata update.'"},
    "Factual content and explicit self-description of the June 3, 2025 NIST notice.",
    "verified"
)

add(
    "Section: How recursive training can fail, line 37",
    "It does not withdraw the report or supply a revised edition.",
    "inference",
    ["R020"],
    {"R020": "Page 1 (single-page list of 5 typographical index entry substitutions)"},
    "Factual clarification preventing misrepresentation of R020 as a withdrawal or second edition of NIST AI 100-2e2025.",
    "qualified"
)

# L39
add(
    "Section: How recursive training can fail, line 39",
    "Use “echo chamber” only as an analogy for feedback, not a substitute for specifying the data-generation, retention and training process.",
    "recommendation",
    [],
    {},
    "Rhetorical and analytical guidance warning against lazy colloquial metaphors.",
    "proposal"
)

add(
    "Section: How recursive training can fail, line 39",
    "Evaluate factual accuracy and rare-case coverage separately from fluency.",
    "recommendation",
    [],
    {},
    "Methodological recommendation emphasizing multi-dimensional evaluation criteria.",
    "proposal"
)

# Section 3: Counterevidence and conditions
# L41
add(
    "Section: Counterevidence and conditions, heading, line 41",
    "## Counterevidence and conditions",
    "recommendation",
    [],
    {},
    "Top-level section heading organizing mitigation strategies, contrary findings, and empirical limits.",
    "proposal"
)

# L43
add(
    "Section: Counterevidence and conditions, subsection 1 heading, line 43",
    "### Original-data retention is useful, but is not a universal cure",
    "recommendation",
    [],
    {},
    "Subsection heading encapsulating the balanced synthesis on data retention.",
    "proposal"
)

# L47 (Kazdan et al. R040, R004)
add(
    "Section: Counterevidence and conditions, line 47",
    "Kazdan et al. distinguish **replacement**, **training on an expanding accumulated pool**, and **accumulating a pool but training on fixed-size subsamples**.",
    "fact",
    ["R004", "R040"],
    {
        "R004": "Abstract, p. 1 and §1",
        "R040": "Abstract, p. 1 and §§2-3"
    },
    "Factual taxonomy of three distinct data usage workflows analyzed in Kazdan et al.",
    "verified"
)

add(
    "Section: Counterevidence and conditions, line 47",
    "The last incurs more loss than full accumulation in the reported comparisons, although loss commonly plateaus rather than diverging.",
    "fact",
    ["R004", "R040"],
    {
        "R004": "Abstract, p. 1 and §4, Figure 4",
        "R040": "Abstract, p. 1 and §§3-4, Figure 4"
    },
    "Verified empirical result showing fixed-size subsampling slows degradation compared to pure replacement and often plateaus.",
    "verified"
)

add(
    "Section: Counterevidence and conditions, line 47",
    "Retaining bytes and allocating enough training resources to use them are different interventions.",
    "inference",
    ["R004", "R040"],
    {
        "R004": "§§1 and 5",
        "R040": "§§1 and 5"
    },
    "Crucial operational distinction between passive data preservation and compute-constrained pretraining capacity.",
    "qualified"
)

# L53
add(
    "Section: Counterevidence and conditions, subsection 2 heading, line 53",
    "### Verification must supply relevant information, not merely confidence",
    "recommendation",
    [],
    {},
    "Subsection heading summarizing the critical requirements for synthetic data filtering.",
    "proposal"
)

# L55 (Feng et al. R007)
add(
    "Section: Counterevidence and conditions, line 55",
    "Feng et al. show that selecting generated examples using verifiers can improve results in studied mathematical and summarization tasks.",
    "fact",
    ["R007"],
    {"R007": "Abstract, p. 1 and §§3-7"},
    "Verified empirical result from Feng et al. (ICLR 2025) demonstrating verifier-based data selection prevents collapse on matrix eigenvalues and news summarization.",
    "verified"
)

add(
    "Section: Counterevidence and conditions, line 55",
    "A stronger general-purpose model is not automatically the better selector in their summarization experiment.",
    "fact",
    ["R007"],
    {"R007": "§5.2 and §7, discussion of summarization verifier selection"},
    "Empirical finding showing that model scale alone does not guarantee superior verifier selection efficiency.",
    "verified"
)

# L59 (Gillman et al. R075)
add(
    "Section: Counterevidence and conditions, line 59",
    "Gillman et al. study self-correction using target-aware mathematical correction, class-conditioned image prototypes and physics-based correction of generated human motion.",
    "fact",
    ["R075"],
    {"R075": "Abstract, p. 1 and §§3-7"},
    "Factual description of the three task domains and verification mechanisms investigated in Gillman et al.",
    "verified"
)

add(
    "Section: Counterevidence and conditions, line 59",
    "Their motion-training loop retains the original real dataset.",
    "fact",
    ["R075"],
    {"R075": "§§4-5, Definition 4.1 and human motion experimental setup"},
    "Verified methodological detail confirming that real training data were retained alongside synthetic data.",
    "verified"
)

add(
    "Section: Counterevidence and conditions, line 59",
    "Its reported “100%” synthetic augmentation is a synthetic-to-real ratio of one-to-one, not an entirely synthetic dataset.",
    "fact",
    ["R075"],
    {"R075": "§5 and Definition 4.1, clarifying 100% augmentation means doubling dataset with 1:1 synthetic to real ratio"},
    "Verified clarification of terminology preventing misinterpretation of '100% synthetic' as purely synthetic training.",
    "verified"
)

add(
    "Section: Counterevidence and conditions, line 59",
    "The paper's language-model extension is future work, not an experiment.",
    "fact",
    ["R075"],
    {"R075": "§8, Conclusion and Future Work"},
    "Accurate bounding of paper scope: LLM application is proposed as future exploration, not empirically tested.",
    "verified"
)

# L61
add(
    "Section: Counterevidence and conditions, subsection 3 heading, line 61",
    "### Broader evidence map",
    "recommendation",
    [],
    {},
    "Heading organizing the structured evidence map table.",
    "proposal"
)

add(
    "Section: Counterevidence and conditions, line 63",
    "The entries below summarize the version actually retained or read.",
    "recommendation",
    [],
    {},
    "Introductory note establishing bibliographic fidelity for table entries.",
    "proposal"
)

add(
    "Section: Counterevidence and conditions, line 63",
    "Their conditions matter more than their titles.",
    "recommendation",
    [],
    {},
    "Epistemological principle that operational conditions supersede promotional headlines.",
    "proposal"
)

add(
    "Section: Counterevidence and conditions, line 63",
    "A preprint or author manuscript is identified as such rather than presented as a separately verified final publication.",
    "recommendation",
    [],
    {},
    "Rigorous attribution rule distinguishing preprints from peer-reviewed records.",
    "proposal"
)

# Broader evidence map table rows with FULL sources:
# Row 72: R008
add(
    "Section: Counterevidence and conditions, Evidence map row 72",
    "Rephrased text, textbook-style generation and real/synthetic mixtures have different training and downstream effects.",
    "fact",
    ["R008"],
    {"R008": "Abstract, p. 1 and §§4-6 (comparing rephrased web data vs textbook-style data)"},
    "Verified empirical finding from Kang et al. (EMNLP 2025) across >1,000 LLM pretraining runs.",
    "verified"
)

add(
    "Section: Counterevidence and conditions, Evidence map row 72",
    "These are single-round pretraining comparisons, not repeated-generation guarantees. No universal optimal proportion is adopted.",
    "inference",
    ["R008"],
    {"R008": "Abstract, p. 1 ('single-round (n=1) model training') and §6 Limitations"},
    "Crucial scope qualification: R008 tests single-generation (n=1) pretraining, not multi-generation recursive collapse.",
    "qualified"
)

# Row 73: R010
add(
    "Section: Counterevidence and conditions, Evidence map row 73",
    "Failure-guided generation and uncertainty-based selection improve tested instruction-tuning benchmarks.",
    "fact",
    ["R010"],
    {"R010": "Abstract, p. 1 and §§3-5 (KITE framework description and benchmark scores)"},
    "Empirical finding from Luo et al. (2026) demonstrating task-level instruction tuning improvements using KITE.",
    "verified"
)

add(
    "Section: Counterevidence and conditions, Evidence map row 73",
    "The method uses a stronger external checking/normalization model. Aggregate gains do not certify retention of every skill.",
    "inference",
    ["R010"],
    {"R010": "§3 Methodology (external teacher model guidance) and §6 Discussion"},
    "Methodological qualification noting reliance on external teacher models and uneven skill retention.",
    "qualified"
)

# Row 74: R056
add(
    "Section: Counterevidence and conditions, Evidence map row 74",
    "Tested OLMo-2 7B/13B continual self-training and perplexity-filtering strategies did not improve downstream performance.",
    "fact",
    ["R056"],
    {"R056": "Abstract, p. 1 and §§2-4, Table 1 (EACL 2026)"},
    "Verified empirical null/adverse result from larger-scale OLMo-2 recursive self-training experiments.",
    "verified"
)

add(
    "Section: Counterevidence and conditions, Evidence map row 74",
    "Their embedding-diversity measure did not consistently explain performance changes; these results do not cover every proprietary or larger model.",
    "inference",
    ["R056"],
    {"R056": "§§4-5 and Limitations"},
    "Analytical assessment from the paper's discussion on metric limitations and architectural generalizability.",
    "qualified"
)

# Row 76: R051
add(
    "Section: Counterevidence and conditions, Evidence map row 76",
    "Local utility-based selection can contract modeled diversity even when data accumulate.",
    "fact",
    ["R051"],
    {"R051": "Abstract, p. 1 and §§2-3 (ICML 2026)"},
    "Theoretical and empirical demonstration that selection bias toward high-reward items collapses tail diversity even under accumulation.",
    "verified"
)

add(
    "Section: Counterevidence and conditions, Evidence map row 76",
    "The selection objective and reference distribution matter; retention alone does not neutralize biased use.",
    "inference",
    ["R051"],
    {"R051": "§§1 and 4"},
    "Analytical inference establishing that preserving raw bytes does not guarantee diverse representations if curation algorithms discard tails.",
    "qualified"
)

# Row 78: R053, R055
add(
    "Section: Counterevidence and conditions, Evidence map row 78",
    "Loss changes can delay the paper's task-specific failure diagnostic in some tested settings.",
    "fact",
    ["R053", "R055"],
    {
        "R053": "npj AI 2025, Methods and Results, Table 5 (Truncated Cross-Entropy)",
        "R055": "Supplementary Information, Table S3"
    },
    "Empirical finding showing confidence-aware loss delays failure points in tested classification tasks.",
    "verified"
)

add(
    "Section: Counterevidence and conditions, Evidence map row 78",
    "Table 5 includes settings worse than the cross-entropy baseline; the intervention is not uniformly beneficial.",
    "inference",
    ["R053"],
    {"R053": "Table 5 and §3 Discussion"},
    "Analytical inspection of Table 5 data revealing non-uniform performance across hyperparameter regimes.",
    "qualified"
)

# Row 79: R054
add(
    "Section: Counterevidence and conditions, Evidence map row 79",
    "Recursive code-training experiments compare external checks and self-coupled review policies.",
    "fact",
    ["R054"],
    {"R054": "Abstract, p. 1 and §§2-3 (comparing No Review, Human-Gate, and AI-Self-Gate)"},
    "Factual description of experimental design in code LLM self-training.",
    "verified"
)

add(
    "Section: Counterevidence and conditions, Evidence map row 79",
    "Self-gate behavior depends on its acceptance rule; a self-review loop is not an independent correctness certificate.",
    "inference",
    ["R054"],
    {"R054": "§§3-4 and Conclusion"},
    "Analytical inference showing that model-coupled code review reproduces and entrenches the model's own systematic coding defects.",
    "qualified"
)

# Row 81: R059
add(
    "Section: Counterevidence and conditions, Evidence map row 81",
    "Evidence-based question answering and fact-verification tasks can use substantial synthetic replacement with retained human examples.",
    "fact",
    ["R059"],
    {"R059": "Abstract, p. 1 and §§2-3"},
    "Empirical finding from task fine-tuning showing synthetic data can substitute for human data when anchor human examples remain.",
    "verified"
)

add(
    "Section: Counterevidence and conditions, Evidence map row 81",
    "This is single-stage task fine-tuning, not recursive-collapse evidence or a universal minimum of human data.",
    "inference",
    ["R059"],
    {"R059": "§§1 and 4 Limitations"},
    "Vital scope distinction: task-specific fine-tuning with ground-truth references does not model open-ended foundation pretraining collapse.",
    "qualified"
)

# Row 84: R065, R066
add(
    "Section: Counterevidence and conditions, Evidence map row 84",
    "SIMS uses negative score guidance; Neon extrapolates away from self-training weight updates.",
    "fact",
    ["R065", "R066"],
    {
        "R065": "Abstract, p. 1 and §3 (SIMS method description)",
        "R066": "Abstract, p. 1 and §§2-3 (Neon negative weight extrapolation)"
    },
    "Verified algorithmic descriptions of two active self-training stabilization techniques for image diffusion.",
    "verified"
)

add(
    "Section: Counterevidence and conditions, Evidence map row 84",
    "These are designed interventions, not evidence that indiscriminate self-training is safe. Their tests are image-generation settings.",
    "inference",
    ["R065", "R066"],
    {
        "R065": "§§1 and 5",
        "R066": "§§1 and 5"
    },
    "Analytical qualification: active mathematical counteractants in image models do not prove that raw, unmitigated self-training is harmless.",
    "qualified"
)

# Row 86: R076
add(
    "Section: Counterevidence and conditions, Evidence map row 86",
    "Tail truncation, generation sampling and finite coverage affect stylized scaling laws; selected Llama 2-7B fine-tuning experiments test related effects.",
    "fact",
    ["R076"],
    {"R076": "Abstract, p. 1 and §§2-6, Appendix H"},
    "Verified theoretical and empirical findings from Dohmatob et al. (ICML 2024) analyzing scaling law breakdown under recursive tail loss.",
    "verified"
)

add(
    "Section: Counterevidence and conditions, Evidence map row 86",
    "The deterministic-label scaling result does not carry over unchanged to probabilistic targets. No universal contamination threshold follows.",
    "inference",
    ["R076"],
    {"R076": "§§3-4 and §6 Limitations"},
    "Mathematical qualification from the authors explicitly bounding their scaling law results.",
    "qualified"
)

# Row 88: R078
add(
    "Section: Counterevidence and conditions, Evidence map row 88",
    "External observations or prior/regularization can change the modeled closed-loop dynamics.",
    "fact",
    ["R078"],
    {"R078": "Abstract, p. 1 and §§3-5 ('Closed-loop learning in EF' and 'The general case')"},
    "Mathematical findings on exponential family parameter trajectories under closed-loop learning.",
    "verified"
)

add(
    "Section: Counterevidence and conditions, Evidence map row 88",
    "Bounded sufficient statistics and the specified estimation/diffusion approximations constrain the result; there is no LLM-training experiment.",
    "inference",
    ["R078"],
    {"R078": "§§1-2 and §6 Discussion"},
    "Explicit scope boundary noting theoretical restriction to exponential families without natural language pretraining experiments.",
    "qualified"
)

# L90 (R072, R073)
add(
    "Section: Counterevidence and conditions, line 90",
    "R072 remains a screened lead rather than support for quantitative effects: its training-corpus construction and evaluation descriptions require clarification before relying on the reported magnitudes.",
    "inference",
    ["R072"],
    {"R072": "Catalog entry and summary notes: unresolved mixture parameter definition and prompt packing protocol in appendices"},
    "Rigorous evidentiary assessment withholding reliance on preprint effect sizes due to internal protocol discrepancies.",
    "qualified"
)

add(
    "Section: Counterevidence and conditions, line 90",
    "R073 is a stylized economic/policy-model lead, not an empirical evaluation of a defense command.",
    "inference",
    ["R073"],
    {"R073": "Catalog entry and summary notes: preprint economic equilibrium and synthetic data market modeling"},
    "Accurate characterization of R073 as theoretical microeconomic modeling rather than an operational military assessment.",
    "qualified"
)

add(
    "Section: Counterevidence and conditions, line 90",
    "Neither is used to establish an internet-wide failure forecast or organizational necessity.",
    "recommendation",
    [],
    {},
    "Explicit negative scope boundary excluding exploratory leads from core evidentiary reliance.",
    "proposal"
)

# L92 (Synthesis)
add(
    "Section: Counterevidence and conditions, Synthesis, line 92",
    "**Synthesis:** the evidence supports a conditional reliability concern and the value of preserving options for checking and retraining.",
    "inference",
    ["R001", "R004", "R007", "R040"],
    {
        "R001": "Nature 2024, pp. 757-759",
        "R004": "Abstract and §4",
        "R007": "Abstract and §§3-7",
        "R040": "Abstract and §§2-4"
    },
    "High-level evidence synthesis capturing the conditional nature of model degradation and the strategic utility of preserved baseline data.",
    "qualified"
)

add(
    "Section: Counterevidence and conditions, Synthesis, line 92",
    "It does not establish inevitable internet-wide collapse, a deadline for failure, or a measured effect on hypothetical superintelligence.",
    "inference",
    ["R001", "R013", "R033"],
    {
        "R001": "Nature 2024, p. 759",
        "R013": "Abstract, p. 1 and Discussion",
        "R033": "§§1-3"
    },
    "Critical negative analytical finding refuting alarmist claims of inevitable collapse, apocalyptic deadlines, or speculative superintelligence effects.",
    "qualified"
)

add(
    "Section: Counterevidence and conditions, Synthesis, line 92",
    "Nor does it establish a universally safe synthetic-data fraction.",
    "inference",
    ["R008", "R076"],
    {
        "R008": "Abstract and §6 Limitations",
        "R076": "§6 Limitations"
    },
    "Analytical finding that optimal or safe synthetic mixing ratios are strictly task-, model-, and pipeline-dependent.",
    "qualified"
)

add(
    "Section: Counterevidence and conditions, Synthesis, line 92",
    "Preserve access to originals, continue acquiring relevant fresh observations, and evaluate the actual training and deployment pipeline; these are complementary recommendations, not a theorem that an archive alone prevents degradation.",
    "recommendation",
    [],
    {},
    "Final policy synthesis articulating actionable recommendations while acknowledging preservation's realistic boundaries.",
    "proposal"
)

print(f"Total claims compiled: {len(claims)}")
assert len(claims) <= 499
assert all(c["claim_id"].startswith("C0") for c in claims)

# Save to local://research-science-audit.jsonl
with open("local://research-science-audit.jsonl", "w") as f:
    for c in claims:
        f.write(json.dumps(c) + "\n")

print("Saved to local://research-science-audit.jsonl")
