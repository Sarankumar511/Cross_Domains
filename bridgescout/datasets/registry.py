"""Domain registry: every collectable domain, its sub-areas, and its sources.

``Disease`` uses PubMed + arXiv (see :mod:`bridgescout.datasets.disease`). The
five method-rich domains below use arXiv + OpenAlex, since they hold the kinds
of solutions BridgeScout should surface for disease research gaps:

    Disease gap                         -> domain that solved the analogue
    sensor noise / artifacts            -> SignalProcessing
    subtle-change detection, forecasts  -> EarthEnvironment
    scarce labels, class imbalance      -> Agriculture
    early deterioration / failure       -> IndustrialReliability
    rare-event detection, explainability-> Finance
"""

from __future__ import annotations

from dataclasses import dataclass, field

from bridgescout.datasets.disease import DISEASE_AREAS


@dataclass(frozen=True)
class DomainSpec:
    name: str
    sources: tuple[str, ...]
    areas: dict[str, dict[str, str]] = field(default_factory=dict)


def _aq(arxiv: str, openalex: str) -> dict[str, str]:
    return {"arxiv": arxiv, "openalex": openalex}


SIGNAL_PROCESSING_AREAS = {
    "Denoising": _aq(
        "signal denoising OR wavelet denoising OR deep denoiser",
        "signal denoising noise removal time series",
    ),
    "BlindSourceSeparation": _aq(
        "blind source separation OR independent component analysis OR source separation",
        "blind source separation independent component analysis",
    ),
    "FaultDetection": _aq(
        "fault detection signal OR fault diagnosis sensor OR change point detection",
        "fault detection diagnosis sensor signals",
    ),
    "TimeSeriesForecasting": _aq(
        "time series forecasting OR sequence forecasting deep learning",
        "time series forecasting prediction",
    ),
    "AnomalyDetection": _aq(
        "anomaly detection time series OR novelty detection signals",
        "anomaly detection time series sensor",
    ),
    "CompressedSensing": _aq(
        "compressed sensing OR sparse signal recovery OR sparse reconstruction",
        "compressed sensing sparse signal recovery",
    ),
    "SpeechAudio": _aq(
        "speech enhancement OR audio source separation OR acoustic signal processing",
        "speech enhancement audio signal processing",
    ),
    "RadarSonar": _aq(
        "radar signal processing OR sonar signal processing OR array signal processing",
        "radar sonar array signal processing",
    ),
}

EARTH_ENVIRONMENT_AREAS = {
    "RemoteSensing": _aq(
        "remote sensing classification OR satellite image segmentation OR hyperspectral imaging",
        "remote sensing satellite image classification",
    ),
    "Seismology": _aq(
        "seismic signal OR earthquake detection OR seismic waveform deep learning",
        "seismology earthquake seismic waveform detection",
    ),
    "ClimateModeling": _aq(
        "climate model OR climate prediction machine learning OR downscaling climate",
        "climate modeling prediction downscaling",
    ),
    "Hydrology": _aq(
        "streamflow prediction OR rainfall runoff model OR hydrological forecasting",
        "hydrology streamflow rainfall runoff forecasting",
    ),
    "AirQuality": _aq(
        "air quality prediction OR PM2.5 forecasting OR pollution estimation",
        "air quality pollution PM2.5 forecasting",
    ),
    "NaturalHazards": _aq(
        "flood forecasting OR wildfire detection OR landslide prediction",
        "flood wildfire landslide hazard prediction",
    ),
    "Oceanography": _aq(
        "ocean forecasting OR sea surface temperature prediction OR ocean remote sensing",
        "oceanography sea surface temperature ocean model",
    ),
    "GeospatialMapping": _aq(
        "land cover mapping OR change detection satellite OR spatial interpolation",
        "land cover change detection geospatial mapping",
    ),
}

AGRICULTURE_AREAS = {
    "CropDiseaseDetection": _aq(
        "crop disease detection OR plant disease classification leaf image",
        "crop plant disease detection leaf image classification",
    ),
    "YieldPrediction": _aq(
        "crop yield prediction OR yield forecasting remote sensing",
        "crop yield prediction forecasting",
    ),
    "PrecisionAgriculture": _aq(
        "precision agriculture OR UAV crop monitoring OR agricultural remote sensing",
        "precision agriculture UAV crop monitoring",
    ),
    "WeedPestDetection": _aq(
        "weed detection OR pest detection deep learning OR insect classification",
        "weed pest insect detection agriculture",
    ),
    "PlantPhenotyping": _aq(
        "plant phenotyping OR plant organ segmentation OR growth stage classification",
        "plant phenotyping image segmentation growth",
    ),
    "SoilMonitoring": _aq(
        "soil moisture estimation OR soil property prediction spectroscopy",
        "soil moisture property prediction sensing",
    ),
    "LivestockMonitoring": _aq(
        "livestock monitoring OR animal behavior recognition OR cattle detection",
        "livestock animal behavior monitoring recognition",
    ),
    "FewShotAugmentation": _aq(
        "few-shot learning agriculture OR data augmentation plant images OR synthetic crop data",
        "few-shot learning data augmentation agriculture images",
    ),
}

INDUSTRIAL_RELIABILITY_AREAS = {
    "PredictiveMaintenance": _aq(
        "predictive maintenance OR machine health monitoring OR condition monitoring",
        "predictive maintenance condition monitoring machinery",
    ),
    "RemainingUsefulLife": _aq(
        "remaining useful life prediction OR prognostics health management",
        "remaining useful life prognostics degradation",
    ),
    "BearingFaultDiagnosis": _aq(
        "bearing fault diagnosis OR rotating machinery fault OR vibration fault classification",
        "bearing fault diagnosis rotating machinery vibration",
    ),
    "QualityInspection": _aq(
        "surface defect detection OR industrial visual inspection OR manufacturing defect classification",
        "surface defect detection visual inspection manufacturing",
    ),
    "ProcessMonitoring": _aq(
        "statistical process monitoring OR multivariate process control OR fault detection process industry",
        "process monitoring fault detection manufacturing",
    ),
    "DigitalTwin": _aq(
        "digital twin manufacturing OR digital twin predictive OR simulation to reality industrial",
        "digital twin manufacturing simulation",
    ),
    "VibrationAnalysis": _aq(
        "vibration signal analysis OR structural vibration monitoring OR modal analysis machine learning",
        "vibration signal analysis structural monitoring",
    ),
    "AnomalyDetection": _aq(
        "industrial anomaly detection OR sensor anomaly detection manufacturing",
        "industrial sensor anomaly detection",
    ),
}

FINANCE_AREAS = {
    "FraudDetection": _aq(
        "financial fraud detection OR credit card fraud detection OR transaction anomaly detection",
        "financial fraud detection transaction anomaly",
    ),
    "CreditRiskScoring": _aq(
        "credit risk modeling OR credit scoring machine learning OR default prediction",
        "credit risk scoring default prediction",
    ),
    "StockForecasting": _aq(
        "stock price prediction OR financial time series forecasting OR volatility forecasting",
        "stock price financial time series forecasting",
    ),
    "AlgorithmicTrading": _aq(
        "algorithmic trading reinforcement learning OR trading strategy machine learning",
        "algorithmic trading strategy reinforcement learning",
    ),
    "RiskManagement": _aq(
        "value at risk estimation OR systemic risk OR financial risk management model",
        "value at risk systemic financial risk management",
    ),
    "PortfolioOptimization": _aq(
        "portfolio optimization OR asset allocation machine learning OR mean variance optimization",
        "portfolio optimization asset allocation",
    ),
    "FinancialNLP": _aq(
        "financial news sentiment OR earnings call analysis NLP OR financial text mining",
        "financial news sentiment text mining NLP",
    ),
    "MarketAnomalyDetection": _aq(
        "market manipulation detection OR anomalous trading pattern OR financial market anomaly",
        "market anomaly manipulation detection trading",
    ),
}

_METHOD_SOURCES = ("arxiv", "openalex")

DOMAINS: dict[str, DomainSpec] = {
    "Disease": DomainSpec("Disease", ("pubmed", "arxiv"), DISEASE_AREAS),
    "SignalProcessing": DomainSpec("SignalProcessing", _METHOD_SOURCES, SIGNAL_PROCESSING_AREAS),
    "EarthEnvironment": DomainSpec("EarthEnvironment", _METHOD_SOURCES, EARTH_ENVIRONMENT_AREAS),
    "Agriculture": DomainSpec("Agriculture", _METHOD_SOURCES, AGRICULTURE_AREAS),
    "IndustrialReliability": DomainSpec(
        "IndustrialReliability", _METHOD_SOURCES, INDUSTRIAL_RELIABILITY_AREAS
    ),
    "Finance": DomainSpec("Finance", _METHOD_SOURCES, FINANCE_AREAS),
}

# The five added in this phase (everything except the already-built Disease).
METHOD_DOMAINS = tuple(name for name in DOMAINS if name != "Disease")
