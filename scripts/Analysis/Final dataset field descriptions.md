# SJMM SUF Release 2024 — Field descriptions (from codebook)

Source: `669_SJMM_Doc_Codebook_EN.html` (SUF Release 2024 codebook export).

Total variables parsed: 77


## adve_*


### `adve_iden_sjob`

- **Definition:** Job ID (each ad is assigned an individual ID)

- **Data type:** character

- **Missing:** 0 (complete rate 1)


### `adve_iden_adve`

- **Definition:** The ad ID (an individual identification number assigned
each ad) enables linking the coded variables with the ad texts.

- **Data type:** character

- **Missing:** 0 (complete rate 1)


### `adve_time_year`

- **Definition:** Year of data collection

- **Data type:** numeric

- **Missing:** 0 (complete rate 1)

- **Range (observed):** 1950 … 2024


### `adve_lang_lang`

- **Definition:** Language of job ad

- **Data type:** haven_labelled

- **Missing:** 0 (complete rate 1)

- **Value labels:**

  - `0` = german

  - `1` = french

  - `2` = italian

  - `3` = english

  - `4` = other


### `adve_chan_gene`

- **Definition:** Advertising channel

- **Data type:** haven_labelled

- **Missing:** 0 (complete rate 1)

- **Value labels:**

  - `1` = 1 press

  - `2` = 2 firm websites

  - `3` = 3 job portals


### `adve_chan_type`

- **Definition:** Subtype of advertising channel

- **Data type:** haven_labelled

- **Missing:** 0 (complete rate 1)

- **Value labels:**

  - `1` = 1 firm panel 2001 manual/press/boards

  - `2` = 2 firm panel 2011 manual

  - `4` = 4 firm panel 2021 manual

  - `5` = 5 firm panel 2021 extern


### `adve_jobn_numb`

- **Definition:** Job number for individual ad (since 2022 == 0, because
the data set only includes advertisements with one job)

- **Data type:** numeric

- **Missing:** 0 (complete rate 1)

- **Range (observed):** 0 … 10


### `adve_empl_nraw`

- **Definition:** Number of employees wanted for the position
advertised

- **Data type:** haven_labelled

- **Missing:** 0 (complete rate 1)

- **Value labels:**

  - `999` = unknown number


### `adve_empl_nrec`

- **Definition:** Number of employees wanted for the position advertised,
recoded on the basis of number (999 more than one, but number
unspecified = 2; values higher than 20 are truncated to 20).

- **Data type:** numeric

- **Missing:** 0 (complete rate 1)

- **Range (observed):** 1 … 20


## comp_*


### `comp_busi_size`

- **Definition:** The size of the business in which the advertised job
opening is located (number of employees)

- **Data type:** haven_labelled

- **Missing:** 0 (complete rate 1)

- **Value labels:**

  - `0` = 0 small

  - `1` = 1 medium/unknown

  - `2` = 2 large


### `comp_sect_publ`

- **Definition:** Public-sector enterprise

- **Data type:** haven_labelled

- **Missing:** 0 (complete rate 1)

- **Value labels:**

  - `0` = no

  - `1` = yes


### `comp_indu_noga`

- **Definition:** NOGA 2008 (two digits), categories with small numbers
of job ads were collapsed according to proximity in classification

- **Data type:** haven_labelled

- **Missing:** 0 (complete rate 1)

- **Additional helper fields:**
  - `comp_indu_noga_label` (string): English label for the NOGA division, mapped from `External datasets/Cross-walks/comp_indu_noga_noga2_and_noga_section_crosswalk.csv`.


### `comp_recr_agen`

- **Definition:** Type of ad (ad by employer vs. by various job placement
entities). Variable is recorded for the channels press and job
portals.

- **Data type:** haven_labelled

- **Missing:** 0 (complete rate 1)

- **Value labels:**

  - `0` = 0 none

  - `1` = 1 headhunter/temporary employment agency/other agency
(association, etc.)


## incu_*


### `incu_educ_ide1`

- **Definition:** Education/training according to the SJMM education
database

- **Data type:** haven_labelled

- **Missing:** 8907 (complete rate 0.9189167)


### `incu_educ_ide2`

- **Definition:** Education/training 2 according to the SJMM education
database

- **Data type:** haven_labelled

- **Missing:** 8277 (complete rate 0.9246518)


### `incu_educ_typ1`

- **Definition:** Duration of education/training 1 according to the SJMM
education database, added via the education code
( in_edu_ide1 ).

- **Data type:** haven_labelled

- **Missing:** 36217 (complete rate 0.670305)

- **Value labels:**

  - `NA` = -9 not applicable (no education specified)

  - `NA` = -8 not recorded for jobs no. 5-10

  - `NA` = -5 not recorded for apprenticeships

  - `1` = 1 compulsory education

  - `2` = 2 two-year VET

  - `3` = 3 three to four-year VET

  - `4` = 4 higher vocational education

  - `5` = 5 university of applied sciences and predecessors

  - `6` = 6 university

  - `7` = 7 postgraduate degree

  - `8` = 8 other school-based education


### `incu_educ_typ2`

- **Definition:** Type of education/training 2 according to the SJMM
education database, added via the education code
( in_edu_ide2 ).

- **Data type:** haven_labelled

- **Missing:** 90678 (complete rate 0.1745289)

- **Value labels:**

  - `NA` = -9 not applicable (no education specified)

  - `NA` = -8 not recorded for jobs no. 5-10

  - `NA` = -5 not recorded for apprenticeships

  - `2` = 2 two-year VET

  - `3` = 3 three to four-year VET

  - `4` = 4 higher vocational education

  - `5` = 5 university of applied sciences and predecessors

  - `6` = 6 university

  - `7` = 7 postgraduate degree

  - `8` = 8 other school-based education


### `incu_educ_yrs1`

- **Definition:** Duration of education/training 1 (post-compulsory, in
years) according to the SJMM education database, added via the
education/training code ( in_edu_ide1 ).

- **Data type:** haven_labelled

- **Missing:** 36217 (complete rate 0.670305)


### `incu_educ_yrs2`

- **Definition:** Duration of education/training 2 (post-compulsory, in
years) according to the SJMM education database, added via the education
code ( in_edu_ide2 ).

- **Data type:** haven_labelled

- **Missing:** 90678 (complete rate 0.1745289)


### `incu_educ_yrsm`

- **Definition:** 

- **Data type:** haven_labelled

- **Missing:** 8915 (complete rate 0.9188439)


### `incu_expe_gene`

- **Definition:** Information on required experience

- **Data type:** haven_labelled

- **Missing:** 2052 (complete rate 0.98132)

- **Value labels:**

  - `NA` = -8 not recorded for jobs no. 5-10

  - `0` = 0 not specified/not necessary

  - `1` = 1 an asset/as an alternative

  - `2` = 2 necessary


### `incu_skil_gene`

- **Definition:** Information on the knowledge/skills required Variable
has been recorded since 1995.

- **Data type:** haven_labelled

- **Missing:** 30733 (complete rate 0.7202276)

- **Value labels:**

  - `NA` = -8 not recorded for jobs no. 5-10

  - `NA` = -7 not recorded for respective year

  - `0` = 0 not specified/not necessary

  - `1` = 1 an asset/as an alternative

  - `2` = 2 necessary


### `incu_trai_gene`

- **Definition:** Information on required advanced training. Variable has
been recorded since 2001.

- **Data type:** haven_labelled

- **Missing:** 34637 (complete rate 0.6846882)

- **Value labels:**

  - `NA` = -8 not recorded for jobs no. 5-10

  - `NA` = -7 not recorded for respective year

  - `0` = 0 not specified/not necessary

  - `1` = 1 an asset/as an alternative

  - `2` = 2 necessary


### `incu_agei_mini`

- **Definition:** Minimum age of the employee wanted.

- **Data type:** haven_labelled

- **Missing:** 103918 (complete rate 0.0540009)

- **Value labels:**

  - `NA` = -8 not recorded for jobs no. 5-10

  - `NA` = -1 not specified


### `incu_agei_maxi`

- **Definition:** Maximum age of the employee wanted.

- **Data type:** haven_labelled

- **Missing:** 104664 (complete rate 0.0472098)

- **Value labels:**

  - `NA` = -8 not recorded for jobs no. 5-10

  - `NA` = -1 not specified


### `incu_agei_rela`

- **Definition:** Relative age of the employee wanted.

- **Data type:** haven_labelled

- **Missing:** 2052 (complete rate 0.98132)

- **Value labels:**

  - `NA` = -8 not recorded for jobs no. 5-10

  - `0` = 0 young

  - `1` = 1 not specified

  - `2` = 2 middle-aged/older/does not matter


### `incu_gend_indi`

- **Definition:** Gender of the employee wanted.

- **Data type:** haven_labelled

- **Missing:** 2052 (complete rate 0.98132)

- **Value labels:**

  - `NA` = -8 not recorded for jobs no. 5-10

  - `0` = 0 male

  - `1` = 1 neutral

  - `2` = 2 female


### `incu_nati_indi`

- **Definition:** Nationality of the employee wanted.

- **Data type:** haven_labelled

- **Missing:** 2052 (complete rate 0.98132)

- **Value labels:**

  - `NA` = -8 not recorded for jobs no. 5-10

  - `0` = 0 not specified

  - `1` = 1 foreigners as well

  - `2` = 2 swiss only


## loca_*


### `loca_muni_iden`

- **Definition:** Place of work: number of municipality according to SFSO
2022, complemented by our own project codes for cantons and regions. The
project codes (7001–9996) are to be used in the event that the ad allows
only a rough classification by geographic location or the job is located
in communities close to the border in neighboring countries. See https://www.bfs.admin.ch/bfs/de/home/statistiken/querschnittsthemen/raeumliche-analysen/raeumliche-gliederungen/analyseregionen.html

- **Data type:** numeric

- **Missing:** 0 (complete rate 1)

- **Range (observed):** 0 … 9996


### `loca_muni_name`

- **Definition:** Location of the business offering the advertised
job.

- **Data type:** character

- **Missing:** 0 (complete rate 1)


### `loca_labo_reg1`

- **Definition:** Place of work: labour market regions according to the
Swiss geographic classification of SFSO. See https://www.bfs.admin.ch/bfs/de/home/statistiken/querschnittsthemen/raeumliche-analysen/raeumliche-gliederungen/analyseregionen.html

- **Data type:** haven_labelled

- **Missing:** 17192 (complete rate 0.8434957)


### `loca_labo_reg2`

- **Definition:** Place of work: large labour market regions according to
the Swiss geographic classification of SFSO. See https://www.bfs.admin.ch/bfs/de/home/statistiken/querschnittsthemen/raeumliche-analysen/raeumliche-gliederungen/analyseregionen.html

- **Data type:** haven_labelled

- **Missing:** 12964 (complete rate 0.8819845)

- **Value labels:**

  - `NA` = -9 not applicable (no education specified)

  - `NA` = -3 not applicable (not assignable to region)

  - `1` = 1 Region Genf

  - `2` = 2 Region Lausanne

  - `3` = 3 Region Neuenburg

  - `4` = 4 Region Freiburg

  - `5` = 5 Region Biel–Jura

  - `6` = 6 Region Bern

  - `7` = 7 Westalpen

  - `8` = 8 Region Basel

  - `9` = 9 Berner Oberland

  - `10` = 10 Aareland

  - `11` = 11 Zentralschweiz

  - `12` = 12 Region Zürich

  - `13` = 13 Sopraceneri

  - `14` = 14 Sottoceneri

  - `15` = 15 Bodenseeregion

  - `16` = 16 Ostalpen


### `loca_regi_kant`

- **Definition:** Place of work: canton (NUTS-3). See https://www.bfs.admin.ch/bfs/de/home/statistiken/querschnittsthemen/raeumliche-analysen/raeumliche-gliederungen/analyseregionen.html

- **Data type:** haven_labelled

- **Missing:** 8818 (complete rate 0.9197269)

- **Value labels:**

  - `NA` = -9 not applicable (no education specified)

  - `NA` = -3 not applicable (not assignable to region)

  - `1` = 1 Zurich

  - `2` = 2 Bern

  - `3` = 3 Lucerne

  - `4` = 4 Uri

  - `5` = 5 Schwyz

  - `6` = 6 Obwald

  - `7` = 7 Nidwald

  - `8` = 8 Glarus

  - `9` = 9 Zug

  - `10` = 10 Fribourg

  - `11` = 11 Solothurn

  - `12` = 12 Basel-City

  - `13` = 13 Basel-Land

  - `14` = 14 Schaffhausen

  - `15` = 15 Appenzell Outer Rhodes

  - `16` = 16 Appenzell Inner Rhodes

  - `17` = 17 St. Gallen

  - `18` = 18 Grisons

  - `19` = 19 Argovia

  - `20` = 20 Thurgovia

  - `21` = 21 Ticino

  - `22` = 22 Vaud

  - `23` = 23 Valais

  - `24` = 24 Neuchâtel

  - `25` = 25 Geneva

  - `26` = 26 Jura

  - `0` = 0 not specified


### `loca_regi_nuts`

- **Definition:** Place of work: regions (NUTS-2). See https://www.bfs.admin.ch/bfs/de/home/statistiken/querschnittsthemen/raeumliche-analysen/raeumliche-gliederungen/analyseregionen.html

- **Data type:** haven_labelled

- **Missing:** 8818 (complete rate 0.9197269)

- **Value labels:**

  - `NA` = -9 not applicable (no education specified)

  - `NA` = -3 not applicable (not assignable to region)

  - `1` = 1 Région lémanique

  - `2` = 2 Espace Mittelland

  - `3` = 3 Nordwestschweiz

  - `4` = 4 Zürich

  - `5` = 5 Ostschweiz

  - `6` = 6 Zentralschweiz

  - `7` = 7 Ticino


### `loca_regi_lang`

- **Definition:** Place of work: language region according to the Swiss
geographic classification system 2009 (Raumgliederungen der Schweiz
2009; BFS), added via SFSO 2009 (mun2009). See http://www.bfs.admin.ch/bfs/portal/de/index/infothek/nomenklaturen/blank/blank/raum_glied/01.html .
See Appendix B SJMM Regional Codes.

- **Data type:** haven_labelled

- **Missing:** 7136 (complete rate 0.9350387)

- **Value labels:**

  - `NA` = -9 not applicable (no education specified)

  - `NA` = -3 not applicable (not assignable to region)

  - `1` = 1 german language area

  - `2` = 2 french language area

  - `3` = 3 italian language area

  - `4` = 4 rhaeto-romanic language area

  - `0` = 0 not specified


## meta_*


### `meta_pres_iden`

- **Definition:** Press title

- **Data type:** haven_labelled

- **Missing:** 61414 (complete rate 0.4409285)


### `meta_pres_samp`

- **Definition:** Primary sampling unit (PSU) for the advertising channel
press

- **Data type:** haven_labelled

- **Missing:** 61414 (complete rate 0.4409285)


### `meta_pres_type`

- **Definition:** Type of paper (newspaper vs. advertising paper)

- **Data type:** haven_labelled

- **Missing:** 61414 (complete rate 0.4409285)

- **Value labels:**

  - `0` = newspaper

  - `1` = gazette


### `meta_pres_circ`

- **Definition:** Circulation of paper

- **Data type:** haven_labelled

- **Missing:** 61414 (complete rate 0.4409285)

- **Value labels:**

  - `1` = large

  - `2` = medium

  - `3` = small


### `meta_pres_regi`

- **Definition:** Region of the press survey by place of publication

- **Data type:** haven_labelled

- **Missing:** 61414 (complete rate 0.4409285)

- **Value labels:**

  - `1` = Central Switzerland

  - `2` = Bern and german-speaking West-Switzerland

  - `3` = Zurich and north-eastern Switzerland

  - `4` = Eastern

  - `5` = Basle

  - `6` = Romandy

  - `7` = Tessin


### `meta_pres_stra`

- **Definition:** Stratum of the advertising channel press, recoded as meta_pres_circ and meta_pres_regi (10 * meta_pres_regi + meta_pres_circ ).

- **Data type:** haven_labelled

- **Missing:** 61414 (complete rate 0.4409285)

- **Value labels:**

  - `11` = Central Switzerland, large

  - `12` = Central Switzerland, medium

  - `13` = Central Switzerland, small

  - `21` = Bern and german-speaking West-Switzerland, large

  - `22` = Bern and german-speaking West-Switzerland, medium

  - `23` = Bern and german-speaking West-Switzerland, small

  - `31` = Zurich and north-eastern Switzerland, large

  - `32` = Zurich and north-eastern Switzerland, medium

  - `33` = Zurich and north-eastern Switzerland, small

  - `41` = Eastern Switzerland, large

  - `42` = Eastern Switzerland, medium

  - `43` = Eastern Switzerland, small

  - `51` = Basle, large

  - `52` = Basle, medium

  - `53` = Basle, small

  - `61` = Romandy, large

  - `62` = Romandy, medium

  - `63` = Romandy, small

  - `71` = Tessin, large

  - `72` = Tessin, medium

  - `73` = Tessin, small


### `meta_pres_size`

- **Definition:** Size of job ads in papers (total area in square
centimeters)

- **Data type:** haven_labelled

- **Missing:** 61423 (complete rate 0.4408466)


### `meta_comp_iden`

- **Definition:** Internal SJMM business identifier for the channel
business websites. Primary sampling unit (PSU) for the channel business
websites.

- **Data type:** haven_labelled

- **Missing:** 69497 (complete rate 0.3673464)

- **Value labels:**

  - `NA` = -6 not recorded for respective channel


### `meta_comp_publ`

- **Definition:** Public-sector enterprise according to the Swiss
Business and Enterprise Register (BER), added via meta_comp_iden .

- **Data type:** haven_labelled

- **Missing:** 69497 (complete rate 0.3673464)

- **Value labels:**

  - `NA` = -6 not recorded for respective channel

  - `0` = private

  - `1` = public


### `meta_comp_stra`

- **Definition:** Stratum of the channel business websites.

- **Data type:** haven_labelled

- **Missing:** 69497 (complete rate 0.3673464)


### `meta_boar_iden`

- **Definition:** Name of the online job portal. Primary sampling unit
(PSU) of the channel job portal

- **Data type:** haven_labelled

- **Missing:** 88789 (complete rate 0.1917251)

- **Value labels:**

  - `NA` = -6 not recorded for respective channel

  - `9001` = jobs

  - `9002` = jobwinner

  - `9003` = jobscout24

  - `9004` = topjobs

  - `9005` = stellen

  - `9006` = gate24

  - `9007` = ostjob

  - `9008` = rav

  - `9009` = jobpilot

  - `9010` = jobup

  - `9011` = jobclick

  - `9012` = espace

  - `9013` = telejob

  - `9014` = monster

  - `9015` = alpha

  - `9016` = publicjobs

  - `9017` = linkedin

  - `9018` = nzz

  - `9019` = xing

  - `9020` = suedostschweizjobs


### `meta_boar_stra`

- **Definition:** Sampling category for the respective job portal. A
distinct category is assigned for each year; it has no substantive
meaning and serves the exclusive technical purpose of counting the job
ads per portal.

- **Data type:** haven_labelled

- **Missing:** 88789 (complete rate 0.1917251)

- **Value labels:**

  - `NA` = -6 not recorded for respective channel


## occu_*


### `occu_titl_adve`

- **Definition:** Occupation, copied from ad

- **Data type:** character

- **Missing:** 0 (complete rate 1)


### `occu_stem_code`

- **Definition:** Eight-digit stem code for the occupation according to
the occupational database (SFSO). See https://www.bfs.admin.ch/bfs/de/home/statistiken/arbeit-erwerb/nomenclaturen/ch-isco-19.html

- **Data type:** numeric

- **Missing:** 0 (complete rate 1)

- **Range (observed):** 1.1e+07 … 5.1e+07


### `occu_stem_nfge`

- **Definition:** stem code: female occupation name. See https://www.bfs.admin.ch/bfs/de/home/statistiken/arbeit-erwerb/nomenclaturen/ch-isco-19.html

- **Data type:** character

- **Missing:** 0 (complete rate 1)


### `occu_stem_nmge`

- **Definition:** stem code: male occupation name. See https://www.bfs.admin.ch/bfs/de/home/statistiken/arbeit-erwerb/nomenclaturen/ch-isco-19.html

- **Data type:** character

- **Missing:** 0 (complete rate 1)


### `occu_ssco_2000`

- **Definition:** Type of occupation (five digits) according to SSCO
2000, added via stem code of occupation (stem). See http://www.bfs.admin.ch/bfs/portal/de/index/infothek/nomenklaturen/blank/blank/sbn_2000/01.html .

- **Data type:** haven_labelled

- **Missing:** 2225 (complete rate 0.9797451)


### `occu_isco_ch19`

- **Definition:** Type of occupation (five digits) according to the
occupational codes of the Swiss Standard Classification of Occupations
CH-ISCO-19, added via stem code of occupation (stamm). see https://www.bfs.admin.ch/bfs/en/home/statistics/work-income/nomenclatures/ch-isco-19.html

- **Data type:** haven_labelled

- **Missing:** 219 (complete rate 0.9980064)


### `occu_isco_2008`

- **Definition:** Unit group (four digits) according to the International
Standard Classification of Occupations (ISCO-08), added via the stem
code of occupation (stem). See http://www.bfs.admin.ch/bfs/portal/de/index/infothek/nomenklaturen/blank/blank/isco08/01.html .
See http://www.ilo.org/public/english/bureau/stat/isco/isco08/index.htm .

- **Data type:** haven_labelled

- **Missing:** 219 (complete rate 0.9980064)

- **Additional helper fields:**
  - `occu_isco1_code` (Int64): 1-digit ISCO major group derived from `occu_isco_2008`.
  - `occu_isco2_code` (Int64): 2-digit ISCO sub-major group derived from `occu_isco_2008`.
  - `occu_isco1_label` (string): English label for the ISCO major group, mapped from `External datasets/Cross-walks/isco_major_code_to_label.csv`.
  - `occu_isco2_label` (string): English label for the ISCO 2-digit sub-major group, mapped from `External datasets/Cross-walks/isco_08_submajor_2digit_code_to_label.csv`.


### `occu_stra_isei`

- **Definition:** Occupational status according to the International
Socio-Economic Index of Occupational Status 2008 (ISEI), added via
ISCO-08 (isco08). See Ganzeboom, Harry, de Graaf, Paul, & Treiman,
Donald (1992). A Standard International Socio-Economic Index of
Occupational Staus. Social Science Research 21 (1), 1-56. See Ganzeboom,
Harry & Treiman, Donald. International Stratification and Mobility
File: Conversion Tools. Amsterdam: Department of Social Research
Methodology. http://www.harryganzeboom.nl/ismf/index.htm .

- **Data type:** numeric

- **Missing:** 0 (complete rate 1)

- **Range (observed):** 12 … 89


### `occu_stra_trei`

- **Definition:** Occupational prestige according to Standard
International Occupational Prestige Scale (SIOPS), added via ISCO-08
(isco08). See Ganzeboom, Harry & Treiman, Donald (1996).
Internationally Comparable Measures of Occupational Status for the 1998
International Standard Classification of Occupations. Social Science
Research 25 (3), 201-239. See Ganzeboom, Harry & Treiman, Donald.
International Stratification and Mobility File: Conversion Tools.
Amsterdam: Department of Social Research Methodology. http://www.harryganzeboom.nl/ismf/index.htm .

- **Data type:** numeric

- **Missing:** 0 (complete rate 1)

- **Range (observed):** 13 … 78


## srvy_*


### `srvy_samp_psun`

- **Definition:** Identifier of the primary sampling units (PSU) across
all channels.

- **Data type:** numeric

- **Missing:** 0 (complete rate 1)

- **Range (observed):** 1101101 … 3109020


### `srvy_samp_ssun`

- **Definition:** Identifier of the secondary sampling units (SSU) across
all channels.

- **Data type:** numeric

- **Missing:** 0 (complete rate 1)

- **Range (observed):** 2e+20 … 2e+20


### `srvy_stra_lev1`

- **Definition:** Identifier of the stratum at level 1

- **Data type:** numeric

- **Missing:** 0 (complete rate 1)

- **Range (observed):** 111 … 25810


### `srvy_stra_lev2`

- **Definition:** Identifier of the stratum at level 2

- **Data type:** numeric

- **Missing:** 0 (complete rate 1)

- **Range (observed):** 2e+11 … 2e+11


### `srvy_fpco_lev1`

- **Definition:** Sampling fraction for ad source, dependent on the
stratum at level 1 (strat_level1).

- **Data type:** numeric

- **Missing:** 0 (complete rate 1)

- **Range (observed):** 0.00078 … 1


### `srvy_fpco_lev2`

- **Definition:** Sampling fraction for ad by ad source.

- **Data type:** numeric

- **Missing:** 0 (complete rate 1)

- **Range (observed):** 0.0011 … 1


### `srvy_fpco_lev3`

- **Definition:** Sampling fraction within ad (fully recorded jobs)

- **Data type:** numeric

- **Missing:** 0 (complete rate 1)

- **Range (observed):** 0.4 … 1


### `srvy_wght_raw1`

- **Definition:** Non-truncated weight for all advertising channels at
the ad level. The weight has been adjusted to correct for overlap
between job portals for the years 2006–2012 and for duplicates within
job portals from 2011 onwards. See User Manual, Chapter 1.5.

- **Data type:** haven_labelled

- **Missing:** 0 (complete rate 1)


### `srvy_wght_tru1`

- **Definition:** Truncated weight for all advertising channels at the ad
level. The truncated weight at the job level is 430. The weight has been
adjusted to correct for overlap between job portals for the years
2006–2012 and for duplicates within job portals from 2011 onwards. See
User Manual, Chapter 1.5

- **Data type:** numeric

- **Missing:** 0 (complete rate 1)

- **Range (observed):** 0.2 … 430


### `srvy_wght_raw2`

- **Definition:** Non-truncated weight for all advertising channels,
considering the number of employees wanted per job ad, calculated as
follows: wt1 * number_rec. The weight has been adjusted to correct for
overlap between job portals for the years 2006–2012 and for duplicates
within job portals from 2011 onwards. See User Manual, Chapter 1.5.

- **Data type:** haven_labelled

- **Missing:** 0 (complete rate 1)


### `srvy_wght_tru2`

- **Definition:** Truncated weight for all advertising channels,
considering the number of employees wanted per job ad, calculated as
follows: wt1 * number_rec. The truncated weight at the job level is 380.
In addition, the weight for all jobs advertised by one enterprise
(firm_01 or firm_12) must not be higher than 1,700 per survey. The
weight has been adjusted to correct for overlap between job portals for
the years 2006–2012 and for duplicates within job portals from 2011
onwards. See User Manual, Chapter 1.5.

- **Data type:** numeric

- **Missing:** 0 (complete rate 1)

- **Range (observed):** 0.2 … 380


## vaca_*


### `vaca_task_main`

- **Definition:** Main tasks associated with the position. Variable has
been recorded since 1995.

- **Data type:** haven_labelled

- **Missing:** 30733 (complete rate 0.7202276)

- **Value labels:**

  - `NA` = -8 not recorded for jobs no. 5-10

  - `NA` = -7 not recorded for respective year

  - `0` = 0 analysis/research, controller

  - `1` = 1 agricultural tasks

  - `2` = 2 hospitality services

  - `3` = 3 ironing, cleaning, waste management

  - `4` = 4 disposing, organizing, leading

  - `5` = 5 IT, programming

  - `6` = 6 set up, operator

  - `7` = 7 educating/teaching, advising

  - `8` = 8 manufacturing

  - `9` = 9 installation, assembly, construction

  - `10` = 10 accounting and finance

  - `11` = 11 purchasing/sales, cashier, customer service

  - `12` = 12 store and transport

  - `13` = 13 supervisor, hiring

  - `14` = 14 medical and cosmetical care

  - `15` = 15 planning, engineering, designing/drawing

  - `16` = 16 publishing, creative work

  - `17` = 17 administration of justice

  - `18` = 18 repair, restore

  - `19` = 19 writing, correspondence, administration

  - `20` = 20 guard


### `vaca_posi_mana`

- **Definition:** Management position

- **Data type:** haven_labelled

- **Missing:** 2052 (complete rate 0.98132)

- **Value labels:**

  - `NA` = -8 not recorded for jobs no. 5-10

  - `0` = no

  - `1` = yes


### `vaca_posi_resp`

- **Definition:** Decision-making responsibility associated with the job
advertised. Variable has been recorded since 1995.

- **Data type:** haven_labelled

- **Missing:** 30733 (complete rate 0.7202276)

- **Value labels:**

  - `NA` = -8 not recorded for jobs no. 5-10

  - `NA` = -7 not recorded for respective year

  - `0` = 0 low/not specified

  - `1` = 1 medium/high


### `vaca_type_temp`

- **Definition:** Type of employment: temporary employment

- **Data type:** haven_labelled

- **Missing:** 0 (complete rate 1)

- **Value labels:**

  - `0` = 0 no

  - `1` = 1 yes


### `vaca_type_inte`

- **Definition:** Type of employment: internship

- **Data type:** haven_labelled

- **Missing:** 0 (complete rate 1)

- **Value labels:**

  - `0` = 0 no

  - `1` = 1 yes


### `vaca_type_appr`

- **Definition:** Type of employment: apprenticeship

- **Data type:** haven_labelled

- **Missing:** 0 (complete rate 1)

- **Value labels:**

  - `0` = 0 no

  - `1` = 1 yes


### `vaca_time_type`

- **Definition:** Extent of employment, in categories. Not specified =
full-time

- **Data type:** haven_labelled

- **Missing:** 2052 (complete rate 0.98132)

- **Value labels:**

  - `NA` = -8 not recorded for jobs no. 5-10

  - `0` = 0 marginal part-time (below 50%)

  - `1` = 1 substantial part-time (50-79%)

  - `2` = 2 almost full-time (80-95%)

  - `3` = 3 full-time (96-100%)


### `vaca_time_perc`

- **Definition:** Extent of employment, in percent. Not specified (often
full-time) = -1

- **Data type:** haven_labelled

- **Missing:** 88040 (complete rate 0.1985435)

- **Value labels:**

  - `NA` = -8 not recorded for jobs no. 5-10

  - `NA` = -1 not specified


### `vaca_time_hour`

- **Definition:** Extent of employment, hours per week. Not specified
(often full-time) = -1

- **Data type:** haven_labelled

- **Missing:** 109423 (complete rate 0.0038871)

- **Value labels:**

  - `NA` = -8 not recorded for jobs no. 5-10

  - `NA` = -1 not specified


### `vaca_wage_indi`

- **Definition:** Pay indicated in job advertisement.

- **Data type:** haven_labelled

- **Missing:** 2052 (complete rate 0.98132)

- **Value labels:**

  - `NA` = -8 not recorded for jobs no. 5-10

  - `0` = no

  - `1` = yes, neutrally

  - `2` = yes, positively
---

# Project-specific fields & analysis conventions (Your enriched dataset)

This section documents **non-SJMM** columns you added to the SJMM SUF, plus a few **dataset-wide conventions**
(handling of missing/special codes, weights, and time) so that analyses remain consistent.

## Added (non-SJMM) fields

### `ai_requirement`
**Type:** categorical string (`"False"`, `"Maybe"`, `"True"`; may contain missing values)  
**Meaning:** Your classifier’s assessment of whether a posting explicitly contains AI requirements.  
**Notes / intended use:**  
- Missing values mean the requirement label is genuinely unavailable for those rows (do not auto-fill).  
- If you later compute “AI adoption rate”, document the operational definition you use (e.g., adoption = `"True"` only; `"Maybe"` treated as borderline).

### `occupation_exposure`
**Type:** numeric (float)  
**Meaning:** Occupational AI exposure score mapped onto each job posting via its occupation code (e.g., ISCO/SSCO mapping depending on your pipeline).  
**Missingness:** Typically indicates “no valid mapping / no score available for this occupation-code instance.”  
**Unit/scale:** as defined by your exposure index source (keep consistent across time).

### `industry_exposure`
**Type:** numeric (float)  
**Meaning:** Industry AI exposure score mapped onto each job posting via industry code (e.g., NOGA).  
**Important:** This is the **unweighted** industry exposure; keep for diagnostics only.

### `industry_exposure_weighted`
**Type:** numeric (float)  
**Meaning:** **Preferred industry exposure** score to use in analyses.  
**Important:** Use **`industry_exposure_weighted` instead of `industry_exposure`** for your thesis analyses (per your project convention).  
**Missingness:** Typically indicates “no valid mapping / no score available for this industry-code instance.”  

### `industry_section`
**Type:** string  
**Meaning:** NOGA section code (A–U) mapped from `comp_indu_noga` via the crosswalk.  
**Notes:**  
- Some collapsed `comp_indu_noga` codes map to combined sections; these are labeled explicitly (e.g., `AB`, `DE`) and treated as valid sections.  

### `industry_section_label`
**Type:** string  
**Meaning:** English label for the NOGA section (e.g., “Manufacturing”).  

### `industry_section_exposure`
**Type:** numeric (float)  
**Meaning:** Section-level AI exposure mapped to each posting via `industry_section`.  
**Notes:** Missing only when the source industry code is missing or has no valid NOGA‑2 exposure mapping.  

### `industry_section_exposure_weighted`
**Type:** numeric (float)  
**Meaning:** Weighted section-level AI exposure (preferred section measure).  
**Notes:** Use this instead of `industry_section_exposure` for analyses; missing only when no valid mapping exists.

### `loca_regi_kant_clean`, `loca_regi_nuts_clean`
**Type:** numeric (Int64)  
**Meaning:** Region fields with special negative codes set to missing (e.g., -3/-7/-8/-9 → NA).  
**Use:** Prefer the `_clean` versions for regional aggregations to avoid treating “not assignable” as a real region.  

## Dataset-wide conventions

### Time variable
- Canonical year field: **`adve_time_year`** (integer).  
- Your analysis window: **2010–2024**.

### Weights (SJMM survey weights)
SJMM provides multiple weight variables. In most “market-level” trend or composition analyses you should use the **truncated weights** to reduce sensitivity to extreme values:
- **`srvy_wght_tru1`**: truncated design weight (job-opening focus)  
- **`srvy_wght_tru2`**: truncated modified weight (employees-wanted focus)

When in doubt, compute key results **both weighted and unweighted**, then report weighted as primary (and keep unweighted as robustness / intuition check).

### Special codes / missing values
Many categorical fields use special negative codes (e.g., `-8`) to represent “not recorded / not specified / not applicable” depending on the variable.
**Convention:** For statistical modelling, treat these special codes as missing (NA) unless you explicitly want a separate “not recorded” category.

### Hiring volume fields
The raw “employees wanted” field may contain extreme sentinel values (commonly observed as **999** in practice).
**Convention:** Prefer the reconciled/imputed field **`adve_empl_nrec`** for volume analyses, and treat raw 999-like values in `adve_empl_nraw` as “unspecified / top-coded” when diagnosing data quality.

## Quality checks (recommended quick asserts)
Before running analyses, validate:
- `adve_time_year` is present, integer, and within 2010–2024.
- `ai_requirement` ∈ {`"False"`, `"Maybe"`, `"True"`, missing}.
- Exposure fields are numeric and within your expected scale.
- Weight fields (`srvy_wght_tru1`, `srvy_wght_tru2`) are non-missing and strictly positive.


## Current dataset snapshot (auto-extracted)
- Source parquet: `final_analysis_dataset.parquet`
- Generated on: `2025-12-14T22:22:55`
- SHA256: `1bba53ce80c133bbec3f53eb107de272092f2acc20a7ece074b98bd3e41586b2`
- Rows × cols: **59,794 × 95**
- Year range: **2010–2024**

### Project-added fields (dtypes & missingness)
| Field | dtype | Missing | Missing % | Notes |
|---|---:|---:|---:|---|
| `ai_requirement` | `string` | 55 | 0.09% | Values: False=56,352, Maybe=2,961, True=426, Missing=55 |
| `occupation_exposure` | `Float64` | 5,051 | 8.45% |  |
| `industry_exposure` | `Float64` | 9,624 | 16.10% |  |
| `industry_exposure_weighted` | `Float64` | 9,624 | 16.10% |  |

### Helper fields added by the cleaning pipeline
| Field | dtype | Missing | Missing % | Notes |
|---|---:|---:|---:|---|
| `adve_empl_nraw_unknown` | `boolean` | 0 | 0.00% | False=56,579, True=3,215 |
| `adve_empl_nraw_clean` | `Int64` | 3,215 | 5.38% |  |

### `_clean` fields (special-code → missing)
- Rule applied in dataset build: original value `< 0` → missing in the `_clean` copy; original columns remain unchanged.

| Field | dtype | Missing | Missing % |
|---|---:|---:|---:|
| `vaca_posi_mana_clean` | `Int64` | 468 | 0.78% |
| `vaca_posi_resp_clean` | `Int64` | 468 | 0.78% |
| `incu_expe_gene_clean` | `Int64` | 468 | 0.78% |
| `incu_trai_gene_clean` | `Int64` | 468 | 0.78% |
| `incu_skil_gene_clean` | `Int64` | 468 | 0.78% |
| `incu_educ_ide1_clean` | `Int64` | 4,416 | 7.39% |
| `incu_educ_ide2_clean` | `Int64` | 3,786 | 6.33% |
| `incu_educ_typ1_clean` | `float64` | 10,464 | 17.50% |
| `incu_educ_typ2_clean` | `float64` | 47,050 | 78.69% |
| `incu_educ_yrs1_clean` | `float64` | 10,464 | 17.50% |
| `incu_educ_yrs2_clean` | `float64` | 47,050 | 78.69% |
| `incu_educ_yrsm_clean` | `float64` | 4,424 | 7.40% |
