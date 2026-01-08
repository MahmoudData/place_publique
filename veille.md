# Veille technique – Détection d’objets pour la vidéosurveillance 

## 1. Choix des modèles et performances

### 1.1 Principaux modèles actuels en vidéosurveillance

Les modèles de type **one‑stage** (famille YOLO, SSD, RetinaNet) dominent les usages temps réel en vidéosurveillance, car ils offrent un excellent compromis précision/vitesse pour du flux continu sur GPU ou edge.[1][2]
Les modèles **two‑stage** (Faster R‑CNN, Mask R‑CNN) restent des références en précision sur COCO/VOC, mais leur latence plus élevée les réserve plutôt à des contextes offline ou à faible cadence d’images.[3][4]

Les approches récentes **Transformers** (DETR et variantes) simplifient la pipeline (NMS‑free, entraînement end‑to‑end) mais demandent souvent plus de ressources et sont moins répandues sur edge que les YOLO optimisés.[4]
Pour la vidéosurveillance industrielle, on observe de plus en plus l’utilisation de modèles YOLO “custom” (head spécialisé, backbone allégé ou hybride type YOLO11‑MobileNet) afin de tenir les contraintes GPU/CPU en périphérie (NVR, Raspberry, Jetson).[5][2]

### 1.2 YOLOv8 vs YOLO11 et compromis vitesse / mAP / ressources

YOLOv8 reste très utilisé pour la vidéosurveillance car les variantes n/s/m offrent un bon équilibre mAP / FPS sur GPU modestes et Jetson, avec des latences typiques de 16–25 ms par image (≈40–60 FPS) pour les versions nano/small.[6]
YOLO11 est présenté comme une évolution plus efficace en termes de complexité (réduction de ~30–40% de FLOPs) avec une précision améliorée, notamment sur les petits objets (piétons lointains, véhicules éloignés).[1][5]

Des benchmarks publics indiquent que YOLOv8‑n tourne autour de 61 FPS et YOLO11‑n autour de 57 FPS sur GPU de référence, avec une mAP très proche, YOLO11 prenant légèrement l’avantage sur la qualité globale.[2][6]
Sur des devices contraints comme le Raspberry Pi, YOLO11 quantifié et optimisé (NCNN, INT8) atteint 8–10 FPS en résolution “confortable” (par ex. 640×480), et plus de 25 FPS en abaissant la résolution, ce qui est compatible avec de la vidéosurveillance quasi temps réel.[5]

### 1.3 Autres familles de modèles \& choix selon contexte

Les modèles **Faster R‑CNN / Mask R‑CNN** offrent une mAP élevée et une meilleure segmentation/masque mais au prix d’une latence significative, rarement compatible avec des flux 25 FPS sur hardware limité.[3][4]
Les variantes **DETR / Deformable DETR** sont intéressantes pour des scènes complexes (chevauchement important, foules denses) grâce à leur capacité d’attention globale, mais les implémentations temps réel exigent des GPUs plus puissants ou un débit d’images réduit.[7][4]

Pour un déploiement sur matériel limité (laptop, Colab, mini‑PC), les recommandations sont généralement de :[2][1][5]

- choisir une variante **nano/small** de YOLOv8 ou YOLO11 ;
- réduire la résolution d’entrée (par ex. 640×360) pour tenir le FPS cible ;
- utiliser la quantification (INT8), le pruning léger, voire un backbone mobile (MobileNet, ShuffleNet) dans des architectures hybrides.

***

## 2. Évaluation rigoureuse pour caméras fixes

### 2.1 Métriques principales (mAP, IoU, précision, rappel)

La **mAP** (mean Average Precision) est la métrique standard pour comparer globalement les modèles de détection : mAP@0.5 (IoU=0.5) mesure la capacité à détecter les objets, tandis que mAP@0.5:0.95 (moyenne de 0.5 à 0.95 par pas de 0.05) est plus stricte sur la localisation.[8][4]
L’**IoU** (Intersection over Union) sert de critère de vérité pour décider si une prédiction est correcte, en comparant la zone de recouvrement entre bounding box prédite et vérité terrain.[9][10]

La **précision** (TP / (TP+FP)) mesure la part de détections correctes parmi toutes les détections et est critique si les fausses alarmes sont coûteuses (ex. sécurité).[11][9]
Le **rappel** (TP / (TP+FN)) mesure la capacité du modèle à ne pas rater d’objets et est essentiel pour des applications où rater une personne ou un véhicule est plus grave qu’une fausse alerte.[9][11]

### 2.2 Bonnes pratiques d’évaluation sur scènes de vidéosurveillance

Pour des caméras fixes, il est recommandé de calculer les métriques **par classe et par scénario** (jour/nuit, pluie, foule dense), car la performance peut varier fortement selon les conditions d’éclairage et de densité.[10][11]
Une grille de tests robuste inclut des séquences annotées séparément pour jour, nuit, pluie/neige, backlight (contre‑jour) et variations saisonnières, afin d’anticiper les environnements réels.[12][7]

Une **analyse d’erreurs** systématique (confusions de classes, faux positifs persistants sur reflets/affiches, faux négatifs sur personnes partiellement occultées) aide à identifier les cas extrêmes et à guider la collecte de données complémentaires.[10][9]
Pour les applications de **comptage**, il est utile d’évaluer directement des métriques de comptage (erreur relative de comptage, MAPE, RMSE sur séries temporelles) en plus de la mAP, car de petites erreurs de détection peuvent se compenser ou s’accumuler selon la méthode de comptage.[13]

***

## 3. Données, annotation et robustesse

### 3.1 Sélection et combinaison de datasets

Des ressources comme **Roboflow Universe** et divers jeux de données de trafic (par ex. Cityscapes, KITTI, jeux urbains météo variée) fournissent une base pour les personnes/véhicules, mais sont rarement directement adaptés aux contextes clients (places, ports, stations de ski).[14][3]
Les webcams publiques et flux open data de villes permettent de capturer des scènes spécifiques (ports, places, pistes) mais demandent un nettoyage (sélection de vues stables, cadrage pertinent, qualité suffisante) avant annotation.[12][7]

Pour contrôler la taille du dataset sur laptop/Colab, une pratique courante consiste à :[7][12]

- échantillonner un nombre limité de frames par vidéo (par ex. 1 frame toutes les 2–5 secondes) ;
- équilibrer les contextes (X images jour, Y nuit, Z mauvais temps) plutôt que de tout annoter.

Les jeux de données de **trafic urbain** peuvent être réutilisés pour initialiser un modèle (pré‑entraînement) puis complétés par un petit dataset spécifique au client, afin de limiter le coût d’annotation tout en couvrant la diversité contextuelle.[15][12]
Cette combinaison “dataset public + dataset client ciblé” est un pilier des approches de transfert de domaine en vision, particulièrement pour la météo et les contextes géographiques différents.[3][7]

### 3.2 Stratégies d’annotation pour un entraînement faisable

L’annotation se concentre généralement sur quelques classes prioritaires (personnes, véhicules, parfois vélos, trottinettes, bateaux) pour limiter la complexité et la taille du dataset.[12][7]
Des outils comme Roboflow, CVAT ou Label Studio permettent de partager la charge d’annotation, d’appliquer des règles de qualité (IoU minimum, cohérence de classes) et de gérer les versions de datasets.[11][10]

Une stratégie efficace est l’annotation **itérative** :[12]

- entraînement initial sur un petit jeu annoté ;
- inférence sur de nouvelles vidéos ;
- correction des erreurs (pseudo‑labels) pour enrichir progressivement le dataset là où le modèle se trompe le plus.

***

## 4. Augmentation de données et adaptation de domaine

### 4.1 Augmentation pour météo, saison, angle de caméra

Les **augmentations photométriques** (variation de luminosité, contraste, bruit, flou de mouvement, teinte) permettent de simuler jour/nuit, brouillard léger, pluie ou caméra de qualité inférieure.[7][3]
Des travaux de détection sous météo adverse montrent que ces augmentations, couplées à des images réelles de brouillard/pluie, améliorent la robustesse des modèles entraînés uniquement sur temps clair.[15][3]

Des augmentations **géométriques** (rotation légère, recadrage, zoom, changement de ratio) aident à rendre le modèle moins sensible aux variations d’angle de caméra et de légère reconfiguration de la scène (caméra déplacée de quelques degrés).[10][7]
D’autres techniques comme le mosaic, mixup et random cropping centrés sur les objets sont intégrées dans de nombreux pipelines YOLO pour enrichir les combinaisons de contexte et d’échelle.[16][1]

### 4.2 Adaptation de domaine pour flux webcams hétérogènes

L’**adaptation de domaine** (Domain Adaptation) est clé lorsque l’on déploie un modèle entraîné sur un dataset source (ville A, météo claire) dans un domaine cible (ville B, météo différente, autre style de caméra).[17][3]
Des frameworks de domain adaptation pour la conduite autonome montrent l’intérêt de combiner adaptation image‑niveau (style, météo) et objet‑niveau (features de bounding boxes) pour réduire l’écart entre domaines.[15][3]

Une stratégie efficace consiste à générer un **domaine auxiliaire** via augmentation (images synthétiques brouillard/pluie) et à appliquer une régularisation de distance de feature entre source, auxiliaire et cible, afin de stabiliser les performances entre différents contextes météo.[3][7]
D’autres approches utilisent des pseudo‑labels sur le domaine cible (webcams réelles) : le modèle pré‑entraîné apporte des labels approximatifs, ensuite filtrés et raffinés pour réentraîner le modèle avec un mélange source+cible.[7][12]

***

## 5. Architecture logicielle et pipeline vidéo

### 5.1 Batch périodique vs quasi temps réel

Dans une architecture **batch périodique**, les vidéos sont segmentées (par ex. fichiers de 5 minutes) puis traitées a posteriori pour produire des statistiques de comptage, ce qui simplifie la robustesse (moins de contraintes temps réel) mais augmente la latence.[18][19] 
Le **quasi temps réel** repose sur un pipeline de streaming : frames ou lots de frames sont envoyés en continu à un service d’inférence, qui renvoie les détections à une base de données ou un moteur de streaming, permettant des dashboards en secondes plutôt qu’en minutes.[20][21]

Pour la vidéosurveillance, le quasi temps réel est généralement préféré pour l’alerte ou le monitoring opérationnel, tandis que le batch est suffisant pour des rapports statistiques journaliers ou mensuels.[19][20]
Un compromis classique consiste à traiter toutes les frames en streaming pour la détection immédiate, tout en agrégeant et stockant périodiquement des statistiques agrégées (comptage par intervalle) plutôt que les vidéos brutes pour réduire les coûts et les risques RGPD.[22][20]

### 5.2 Microservices, message queues et scalabilité

Une architecture courante pour relier flux vidéo, inference service, base temporelle et frontend type Flask s’appuie sur :[23][20][18]

- un **ingestor vidéo** (lecture RTSP/HTTP, extraction de frames) ;
- un **bus de messages** (Kafka, RabbitMQ, Redis Streams) qui transporte les tâches d’inférence ;
- un ou plusieurs **services d’inférence** (microservices Docker) qui consomment les frames, exécutent YOLO/Faster R‑CNN et produisent les détections ;
- une **base de données temporelle** (TimescaleDB, InfluxDB, ClickHouse) pour stocker les séries de comptage ;
- un **backend Flask/FastAPI** qui expose des APIs au frontend et aux dashboards.

L’utilisation de message queues permet de découpler la capture vidéo de l’inférence, d’absorber les pics de charge et de maintenir la tolérance aux pannes (si un worker tombe, d’autres reprennent la file).[20][23]
Les architectures orientées **Kappa** (pipeline unique streaming + stockage historique) simplifient la maintenance par rapport aux architectures Lambda (couche batch + couche streaming distinctes), tout en permettant de réentraîner les modèles à partir des logs historiques.[18][20]

***

## 6. MLOps pour la détection d’objets

### 6.1 Outils et patterns MLOps recommandés

**MLflow** est largement utilisé pour suivre les expériences (hyperparamètres, métriques mAP, artefacts de modèles) et versionner les modèles, ce qui facilite la comparaison entre variantes YOLO/DETR lors des essais.[9][11]
Les pratiques de **versioning de modèles** (MLflow Model Registry, DVC ou stockage type S3 avec tags) sont essentielles pour tracer quel modèle est déployé où et avec quel dataset/données d’entraînement.[11][10]

Des pipelines **CI/CD** (GitHub Actions, GitLab CI, Jenkins) permettent d’automatiser :[19][20]

- les tests unitaires et d’intégration du code (pré/post‑processing, API Flask) ;
- les tests d’inférence sur un jeu d’images de validation ;
- la construction d’images Docker et le déploiement sur l’environnement de production (cloud ou on‑premises).

L’utilisation de conteneurs **Docker** pour le service d’inférence (modèle + runtime + dépendances) garantit la reproductibilité entre développement, staging et production, et se combine bien avec Kubernetes pour le scaling horizontal.[20][18]

### 6.2 Tests automatisés et déploiement reproductible

Les pipelines MLOps matures incluent des **tests de non‑régression** sur mAP, précision/rappel par classe et latence, afin de garantir qu’une nouvelle version de modèle n’est pas dégradée par rapport à la version en production.[11][10]
Des tests end‑to‑end peuvent rejouer un sous‑ensemble de flux vidéo représentatifs, mesurer l’erreur de comptage et vérifier des seuils de performance avant de valider la promotion du modèle.[13][9]

Le déploiement reproductible passe par la conservation des métadonnées d’expérience (version du code, hash du dataset, hyperparamètres, seed, environnement) et des images Docker construites à partir de ces métadonnées.[10][11]
Dans les environnements **cloud** ou **on‑premise**, ces pratiques permettent de reconstruire un modèle à l’identique pour audit ou ré‑investigation en cas d’incident, ce qui est particulièrement important dans un contexte réglementé (RGPD/AI Act).[24][22]

***

## 7. Monitoring, dérive et réentraînement

### 7.1 Métriques et signaux de dérive

La **dérive de données** se manifeste par un changement des distributions d’entrées (nouvelles caméras, changements de météo/saison, modification des flux de personnes) et peut provoquer une baisse de performance du modèle en production.[12][7]
La **dérive de concept** correspond à un changement de la relation entrée‑sortie (nouvelles classes, nouveaux comportements, zones piétonnes devenant routières, etc.), nécessitant souvent une mise à jour des labels et du modèle.[7][12]

Les signaux à surveiller incluent :[13][11]

- distributions de caractéristiques simples (taille des bounding boxes, position dans l’image, classes détectées) ;
- taux de détection (nombre moyen d’objets par frame) vs historique ;
- écarts soudains dans les séries temporelles de comptage (anomalies) ;
- feedback utilisateur (tags “erreur” sur des frames, corrections manuelles).

Une chute persistante de métriques de qualité (via audits périodiques annotés) ou des anomalies dans les séries temporelles de comptage (par ex. passage soudain à zéro alors que la caméra fonctionne) peuvent déclencher un **processus de réentraînement**.[13][10]
Ce processus inclut généralement la sélection de nouvelles données représentatives, leur annotation et l’actualisation du modèle, suivie de tests comparatifs avec le modèle actuel.[12][7]

### 7.2 Intégration du monitoring dans l’application

Les plateformes comme **MLflow** et des solutions de monitoring (Prometheus + Grafana, dashboards custom) peuvent être intégrées pour suivre en temps réel :[11][10]

- les métriques de modèle (taux de détection moyen, distribution des classes) ;
- les métriques opérationnelles (latence par requête, utilisation GPU/CPU, nombre de frames droppées).

Des **alertes** (par seuils sur métriques ou détection d’anomalies) peuvent être envoyées aux équipes lorsque la latence explose, que le taux de détection s’effondre, ou que les séries de comptage deviennent incohérentes (ex. pics impossibles).[20][13]
Les métriques agrégées peuvent être exposées au frontend (Flask) via une API dédiée, alimentant des dashboards internes et des rapports clients (qualité de détection, disponibilité du service).[19][20]

***

## 8. RGPD, AI Act et éthique

### 8.1 Classification RGPD et AI Act

Le RGPD considère les **données biométriques** (par ex. reconnaissance faciale pour identifier une personne) comme des données sensibles soumises à des restrictions strictes (Article 9).[24]
Le simple **comptage anonymisé** de personnes ou de véhicules (sans identification ni suivi individuel sur longue durée) peut être traité comme une donnée moins intrusive, mais reste couvert par le RGPD dès lors que la vidéo permet potentiellement d’identifier une personne.[22][24]

L’**AI Act** classe les systèmes de **remote biometric identification en temps réel** dans les espaces publics comme pratiques interdîtes pour la plupart des usages, avec quelques exceptions limitées pour les forces de l’ordre.[25][26]
Les systèmes de reconnaissance biométrique a posteriori (post‑remote) sont classés **à haut risque** et soumis à des obligations renforcées (gestion des risques, gouvernance des données, supervision humaine, enregistrement dans une base européenne).[27][25]

Les systèmes de vidéosurveillance algorithmique sans identification biométrique (par ex. simple détection/comptage) relèvent plutôt de la catégorie haut risque ou limitée selon les cas, impliquant au minimum une analyse d’impact (DPIA), une documentation, un registre et des mesures de transparence.[26][22]
Pour rester conforme, les pratiques techniques recommandées incluent : absence de stockage long terme des vidéos, agrégation des données de comptage, chiffrement, contrôle d’accès strict et suppression automatique.[22][24]

### 8.2 Pratiques de privacy by design

Plusieurs mesures techniques contribuent à la conformité RGPD/AI Act pour le comptage :[24][22]

- traitement **en périphérie** (edge) avec envoi uniquement de métriques de comptage, sans transfert de vidéo brute ;
- floutage ou masquage des visages avant toute persistance ;
- réduction de la résolution ou du champ de vision pour limiter l’identifiabilité.

La **base légale** (intérêt légitime, obligation légale, mission d’intérêt public) doit être clairement documentée, et les responsables de traitement doivent tenir un **registre des activités** ainsi qu’une DPIA pour les installations de vidéosurveillance systématique.[26][24]
Des obligations de **transparence** (panneaux d’information, politiques de confidentialité accessibles) et de limitation des finalités (pas de réutilisation à d’autres fins sans base légale supplémentaire) sont également centrales.[22][24]

### 8.3 Enjeux éthiques du comptage automatisé

Le comptage automatisé de personnes et de véhicules dans l’espace public soulève des risques de **surveillance de masse**, de profilage et de discrimination, en particulier si les données sont croisées avec d’autres sources ou utilisées pour du policing prédictif.[28][27]
Des biais peuvent apparaître si les modèles sont moins performants sur certaines populations (par ex. vêtements, morphologies, conditions d’éclairage propres à certaines régions), ce qui peut entraîner des erreurs ciblées.[29][30]

Les recommandations éthiques incluent :[28][27][22]

- appliquer une réelle **privacy by design** (minimisation de données, anonymisation, agrégation) ;
- limiter strictement les finalités (comptage statistique plutôt que suivi individuel, pas de “scoring” des personnes) ;
- mettre en place une **gouvernance des modèles** (revues régulières, audits indépendants, documentation des jeux de données et des performances par sous‑population).

L’implication des parties prenantes (collectivités, citoyens, experts en éthique) dans la conception des projets et la transparence des algorithmes utilisés peuvent aider à limiter le risque de dérive vers la surveillance généralisée.[31][30]
Enfin, la possibilité de **contestation** (mécanismes de recours, responsables identifiés) et la supervision humaine des décisions critiques restent des éléments centraux d’une approche responsable.[26][24]

***

## 9. Illustration synthétique : choix de modèle selon contrainte

| Contrainte principale | Modèles typiques | Avantages clés | Limites / points d’attention |
| :-- | :-- | :-- | :-- |
| Temps réel sur edge (Raspberry/Jetson) | YOLOv8‑n/s, YOLO11‑n | 40–60 FPS sur GPU modeste, bonne mAP globale [6][5] | Précision moindre que modèles lourds |
| Haute précision hors ligne | Faster/Mask R‑CNN, DETR | Très bonne mAP, localisation fine [3][4] | Latence élevée, peu adapté au 25 FPS |
| Conditions météo difficiles | YOLO + domain adaptation | Robustesse accrue brouillard/pluie [3][15] | Nécessite données cibles et tuning |
| Matériel CPU/NVR limité | YOLO allégé / MobileNet‑YOLO | Faible empreinte, possible temps réel [2] | Compromis mAP vs vitesse important |


***

[1]: https://arxiv.org/html/2510.09653v2

[2]: http://www.diva-portal.org/smash/get/diva2:1970568/FULLTEXT01.pdf

[3]: https://arxiv.org/html/2307.09676v4

[4]: https://www.v7labs.com/blog/mean-average-precision

[5]: https://learnopencv.com/yolo11-on-raspberry-pi/

[6]: https://www.labellerr.com/blog/yolo11-vs-yolov8-model-comparison/

[7]: https://research.chalmers.se/publication/548217/file/548217_Fulltext.pdf

[8]: https://www.homai.no/deep-dive-into-object-detection-metrics-a-complete-evaluation-toolkit

[9]: https://securade.ai/blog/technology/object-detection-metrics-guide.html

[10]: https://blog.roboflow.com/object-detection-metrics/

[11]: https://labelyourdata.com/articles/object-detection-metrics

[12]: https://www.diva-portal.org/smash/get/diva2:1709477/FULLTEXT01.pdf

[13]: https://www.sciencedirect.com/science/article/pii/S1077314225003297

[14]: https://jinlong17.github.io/files/WACV2023_DA_detection_round2.pdf

[15]: https://ieeexplore.ieee.org/abstract/document/10030451

[16]: https://docs.ultralytics.com/compare/yolo11-vs-yolov8/

[17]: https://openaccess.thecvf.com/content/WACV2023/papers/Li_Domain_Adaptive_Object_Detection_for_Autonomous_Driving_Under_Foggy_Weather_WACV_2023_paper.pdf

[18]: https://www.kai-waehner.de/blog/2021/09/23/real-time-kappa-architecture-mainstream-replacing-batch-lambda/

[19]: https://dzone.com/articles/batch-vs-real-time-processing-understanding-the-differences

[20]: https://www.tinybird.co/blog/real-time-streaming-data-architectures-that-scale

[21]: https://www.cs.toronto.edu/~mortazavi/papers/Videopipe_Salehe.pdf

[22]: https://www.dallmeier.com/about-us/dallmeier-blog/video-security-technology-and-biometric-facial-recognition-under-new-eu-ai-act-ai-regulation

[23]: https://stackoverflow.com/questions/51916102/is-microservice-architecture-using-message-queues-and-event-driven-architecture

[24]: https://www.twobirds.com/en/insights/2023/global/biometrics-under-the-eu-ai-act

[25]: https://iapp.org/news/a/biometrics-in-the-eu-navigating-the-gdpr-ai-act

[26]: https://artificialintelligenceact.eu/article/5/

[27]: https://edri.org/our-work/how-to-fight-biometric-mass-surveillance-after-the-ai-act-a-legal-and-practical-guide/

[28]: https://videosurveillance.blog.gov.uk/2019/02/15/driving-ethics-forward-the-importance-of-considering-the-ethics-of-automatic-number-plate-recognition-anpr/

[29]: https://pmc.ncbi.nlm.nih.gov/articles/PMC12148897/

[30]: https://www.frontiersin.org/journals/robotics-and-ai/articles/10.3389/frobt.2025.1544272/full

[31]: https://www.suaave.eu/wp-content/uploads/sites/17/2021/06/Public-perception-of-ethical-issues-concerning-automated-mobility.pdf

