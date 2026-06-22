--
-- PostgreSQL database dump
--

-- Dumped from database version 18.3
-- Dumped by pg_dump version 18.3

-- Started on 2026-06-22 15:11:08

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 221 (class 1259 OID 16556)
-- Name: wb_schemes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.wb_schemes (
    id integer NOT NULL,
    scheme_name character varying,
    scheme_code character varying,
    min_age integer,
    max_age integer,
    max_income integer,
    gender character varying(50),
    caste character varying(50),
    marital_status character varying(50),
    occupation character varying(50),
    residence_area character varying(50),
    school_type character varying(50),
    education character varying(50)
);

ALTER TABLE public.wb_schemes OWNER TO postgres;

--
-- TOC entry 5019 (class 0 OID 16556)
-- Dependencies: 221
-- Data for Name: wb_schemes; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.wb_schemes (id, scheme_name, scheme_code, min_age, max_age, max_income, gender, caste, marital_status, occupation, residence_area, school_type, education) FROM stdin;
1	Old age Pension for Farmer	S014	60	100	999999999	male	Any	Any	Farmer	west bengal	Any	Any
2	Old Age Pension to Handicrafts & Village Industries Artisans under Jai Bangla Scheme	S036	60	100	999999999	male	Any	Any	Handicrafting	west bengal	Any	Any
3	Old Age Pension To Handloom Weavers under Jai Bangla Scheme	S035	60	100	999999999	male	Any	Any	Weaver	west bengal	Any	Any
4	Lok Prasar Prakalpa(Retainer)	S046	1	100	150000	male	Any	Any	Artistic Background	west bengal	Any	Any
5	Lok Prasar Prakalpapa(Pensioner)	S047	1	100	150000	male	Any	Any	Artistic Background	west bengal	Any	Any
6	State Welfare Scheme for Purohits	S048	18	60	150000	male	Any	Any	Priest	west bengal	Any	Any
7	Fishermen old age pension under Jai Bangla	S040	60	100	150000	male	Any	Any	Fisherman	west bengal	Any	Any
8	Taposili Bandhu(SC)	S201	60	100	999999999	male	SC	Any	Any	west bengal	Any	Any
9	Jai Johar	S066	60	100	999999999	male	ST	Any	Any	west bengal	Any	Any
10	Legacy Old Age Pension for ST	S076	60	100	999999999	male	ST	Any	Any	west bengal	Any	Any
11	Manabik under Jai Bangla Pension	S071	1	100	100000	male	Any	Unmarried	Any	west bengal	Any	Any
12	Lakshmir Bhandar	S070	25	60	999999999	Female	Any	Any	Women	west bengal	Any	Any
13	Widow Pension under Jai Bangla Pension	S075	18	100	999999999	Female	Any	Widow	Women	west bengal	Any	Any
14	Old Age Pension under Jai Bangla Pension	S072	60	100	999999999	Male	Any	Any	Any	west bengal	Any	Any
15	Rupashree	S073	18	100	150000	Female	Any	Unmarried	Women	west bengal	Any	Any
16	Kanyashree K1	S069	13	17	120000	Female	Any	Unmarried	Student	west bengal	government	8
17	Kanyashree K2	S069	18	19	120000	Female	Any	Unmarried	Student	west bengal	government	12
\.

--
-- TOC entry 4869 (class 2606 OID 16563)
-- Name: wb_schemes wb_schemes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.wb_schemes
    ADD CONSTRAINT wb_schemes_pkey PRIMARY KEY (id);

-- PostgreSQL database dump complete
--