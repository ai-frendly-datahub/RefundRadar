# RefundRadar Data Sources Research

**Generated:** 2026-03-04  
**Research Duration:** 8m 11s

---

## RSS Feeds (16+ Sources)

### Official Government RSS Feeds

1. **IRS Newsroom RSS** - `https://www.irs.gov/newsroom/rss.xml`
   - Focus: Tax refund news, IRS announcements, tax tips, policy updates
   - Update frequency: Daily/weekly
   - Quality: High (Official US government)

2. **Grants.gov RSS Feeds** - Multiple feeds:
   - New Opportunities: `https://www.grants.gov/rss/GG_NewOppByCategory.xml`
   - Modified Opportunities: `https://www.grants.gov/rss/GG_OppModByAgency.xml`
   - Focus: Federal grant opportunities, funding announcements
   - Update frequency: Daily
   - Quality: High (Official US government)

3. **HUD RSS Feeds** - `https://www.hud.gov/rss/`
   - Focus: Housing subsidies, HUD grants, federal housing assistance
   - Update frequency: Weekly
   - Quality: High (Official US government)

4. **HUDUSER RSS Feeds** - `https://www.huduser.gov/rss/rss.html`
   - Focus: Housing policy research, income limits, grant opportunities
   - Update frequency: Weekly
   - Quality: High (Research-focused)

5. **Federal Register RSS**
   - Focus: Official federal funding notices, grant availability
   - Update frequency: Daily
   - Quality: High (Official legal publication)

6. **Benefits.gov Data Catalog RSS**
   - Focus: Government benefits, assistance programs
   - Update frequency: Weekly
   - Quality: High (Official US government)

7. **Energy Star Rebate Finder** - `https://www.energystar.gov/rebate-finder`
   - Focus: Energy efficiency rebates, appliance rebates
   - Update frequency: Monthly
   - Quality: High (EPA official source)

### Tax & Financial RSS Feeds

8. **Tax Foundation Blog RSS** - `https://taxfoundation.org/blog/feed/`
   - Focus: Tax policy, refund analysis
   - Update frequency: Weekly
   - Quality: High (Reputable think tank)

9. **TaxProf Blog RSS** - `https://taxprof.typepad.com/taxprof_blog/rss.xml`
   - Focus: Tax law updates, refund guidance
   - Update frequency: Weekly
   - Quality: Medium (Academic/professional)

10. **Smart Accountants Blog RSS** - `https://smartaccountants.com/blog/feed/`
    - Focus: Tax refund tips, tax planning
    - Update frequency: Weekly
    - Quality: Medium

11. **Fraud of the Day RSS** - `https://fraudoftheday.com/feed`
    - Focus: Tax fraud cases, refund scams
    - Update frequency: Daily
    - Quality: Medium

12. **NAUPA RSS** (National Association of Unclaimed Property Administrators)
    - Focus: Unclaimed property, tax refunds
    - Update frequency: Weekly
    - Quality: High (Official state-level organization)

13. **Herbein + Company Blog RSS** - `https://herbein.com/blog/rss.xml`
    - Focus: Tax refund strategies, IRS updates
    - Update frequency: Weekly
    - Quality: Medium

---

## APIs (10+ Sources)

### US Government APIs

1. **SAM.gov Assistance Listings Public API**
   - Base URL: `https://api.sam.gov/assistance-listings/v1/search`
   - Documentation: https://open.gsa.gov/api/assistance-listings-api/
   - Authentication: Required (API key from SAM.gov account)
   - Rate limit: 10-1,000 requests/day depending on account type
   - Data: Federal assistance listings, grant programs, subsidy information

2. **Grants.gov Applicant API**
   - Documentation: https://grants.gov/api
   - Authentication: Required (API key registration)
   - Rate limit: 60 requests/minute, 10,000 requests/day
   - Data: Grant opportunities, application details, funding announcements

3. **USAspending API**
   - Base URL: `https://api.usaspending.gov/api/v2/`
   - Documentation: https://api.usaspending.gov/
   - Authentication: Not required for most endpoints
   - Data: Federal spending data, grant awards, agency budgets

4. **Benefits.gov Benefits Eligibility API** (Archived)
   - Documentation: Available on Data.gov
   - Authentication: Not required (public data)
   - Data: Government benefits, eligibility criteria, application information

5. **DSIRE API**
   - Base URL: `https://www.dsireusa.org/dsire-api/`
   - Documentation: https://www.dsireusa.org/dsire-api/
   - Authentication: Required (subscription)
   - Data: State energy incentives, rebates, tax credits (all 50 states)

### Korean Government APIs

6. **보조금24 (Bokji24) API**
   - Endpoint: `http://apis.data.go.kr/1051000/MoefOpenAPI/T_OPD_PRM`
   - Documentation: https://www.data.go.kr/data/15097584/openapi.do
   - Authentication: Not required (public open API)
   - Rate limit: 10,000/day development, unlimited production
   - Data: National subsidy information, budget data, subsidy programs

7. **정부24 (Gov24) Online Application Platform API**
   - Documentation: http://wjdwlsdyd883.dothome.co.kr/html/A24_API-0001.html
   - Authentication: Required (registration)
   - Data: Government benefits, application processing, eligibility verification

8. **행정안전부 Public Service API**
   - Endpoint: `https://www.data.go.kr/data/15113968/openapi.do`
   - Documentation: Available on Data.gov
   - Authentication: Not required
   - Rate limit: 10,000/day
   - Data: Government services, benefit programs

### Third-Party APIs

9. **Rewiring America API**
   - Documentation: https://github.com/rewiringamerica/api.rewiringamerica.org
   - Authentication: Not required (public API)
   - Data: Federal, state, utility rebates, tax credits, electrification incentives

10. **EcoRebates API**
    - Documentation: https://ecorebates.com/
    - Authentication: Required (commercial API)
    - Data: Consumer rebate programs, product incentives

---

## Web Scraping Targets (13+ Sites)

### US Government Scraping Targets

1. **IRS Newsroom** - `https://www.irs.gov/newsroom`
   - Target pages: News releases, tax tips, refund announcements
   - Data format: HTML (structured with articles)
   - Update frequency: Daily

2. **Benefits.gov Benefit Finder** - `https://www.benefits.gov/benefit-finder`
   - Target pages: Benefits search results, eligibility information
   - Data format: HTML with structured benefit cards
   - Update frequency: Weekly

3. **Grants.gov Search Results** - `https://www.grants.gov/search-results-detail/`
   - Target pages: Grant opportunity details, eligibility criteria
   - Data format: HTML
   - Update frequency: Daily

4. **HUD Funding Opportunities** - `https://www.hud.gov/hud-partners/grants-info-funding-opps`
   - Target pages: Notice of Funding Opportunities (NOFOs), award information
   - Data format: HTML tables
   - Update frequency: Weekly

5. **Energy Star Rebate Finder** - `https://www.energystar.gov/rebate-finder`
   - Target pages: State rebate listings, product search results
   - Data format: HTML with product details
   - Update frequency: Monthly

6. **DSIRE Database** - `https://www.dsireusa.org/`
   - Target pages: State incentive summaries, policy details, eligibility
   - Data format: HTML with searchable database
   - Update frequency: Regular updates
   - Coverage: 50 states, 124 technologies

7. **Unclaimed Money Search** - `https://unclaimed.org/search/`
   - Target pages: State unclaimed property databases
   - Data format: HTML forms
   - Update frequency: State-specific

8. **California BOE Unclaimed Property** - `https://scop.propertytaxinfo.boe.ca.gov/`
   - Target pages: Property tax refunds, unclaimed cash
   - Data format: HTML
   - Update frequency: Regular

### Korean Government Scraping Targets

9. **보조금24 (Bokji24)** - `https://www.gov.kr/portal/rcvfvrSvc/svcFind/svcSearchAll`
   - Target pages: All benefit listings, subsidy announcements
   - Data format: HTML with structured benefit cards
   - Update frequency: Real-time
   - Coverage: ~10,000 government benefits

10. **정부24 (Gov24) Subsidy Portal** - `https://www.gov.kr/portal/rcvfvrSvc/main`
    - Target pages: Personalized benefit recommendations, subsidy search
    - Data format: HTML with interactive elements
    - Update frequency: Daily

11. **국세청 (NTS) 홈택스 (Hometax)** - `https://www.hometax.go.kr/`
    - Target pages: Year-end tax refund service, refund announcements
    - Data format: HTML with secure forms
    - Update frequency: Daily during tax season

12. **Data.go.kr Government APIs Portal** - `https://www.bojo.go.kr/ga/retrieveOpnApi.do`
    - Target pages: Open API catalog, subsidy APIs
    - Data format: HTML with API specifications
    - Update frequency: Monthly
    - Coverage: ~200 Korean government APIs

13. **State EV Rebate Programs** (California, New York, Colorado, etc.)
    - Target pages: EV rebate applications, incentive calculators
    - Data format: HTML forms
    - Update frequency: Monthly/quarterly

---

## Recommended Configuration

### Top 15 Sources for `config/categories/refund.yaml`

```yaml
sources:
  # US Government - Tax Refunds
  - name: IRS Newsroom
    url: https://www.irs.gov/newsroom/rss.xml
    type: rss
    focus: tax-refund
    priority: high
    country: US
  
  - name: SAM.gov Assistance Listings API
    url: https://api.sam.gov/assistance-listings/v1/search
    type: api
    focus: subsidies
    priority: high
    country: US
    requires_api_key: true
  
  - name: Grants.gov API
    url: https://grants.gov/api
    type: api
    focus: grants
    priority: high
    country: US
  
  - name: Benefits.gov Data Catalog
    url: https://catalog.data.gov/dataset/benefits-gov
    type: api
    focus: benefits
    priority: high
    country: US
  
  # US Government - Housing & Energy
  - name: HUD Funding Opportunities
    url: https://www.hud.gov/hud-partners/grants-info-funding-opps
    type: scrape
    focus: housing-grants
    priority: high
    country: US
  
  - name: Energy Star Rebate Finder
    url: https://www.energystar.gov/rebate-finder
    type: scrape
    focus: energy-rebates
    priority: high
    country: US
  
  - name: DSIRE API
    url: https://www.dsireusa.org/dsire-api/
    type: api
    focus: energy-incentives
    priority: high
    country: US
  
  # Korean Government - Tax Refunds & Subsidies
  - name: 국세청 홈택스 (Hometax)
    url: https://www.hometax.go.kr/
    type: scrape
    focus: korean-tax-refund
    priority: high
    country: KR
  
  - name: 보조금24 (Bokji24)
    url: https://www.gov.kr/portal/rcvfvrSvc/svcFind/svcSearchAll
    type: api
    focus: korean-subsidies
    priority: high
    country: KR
    requires_api_key: false
  
  - name: 정부24 보조금 API
    url: http://apis.data.go.kr/1051000/MoefOpenAPI/T_OPD_PRM
    type: api
    focus: korean-government-subsidies
    priority: high
    country: KR
    requires_api_key: false
  
  - name: Rewiring America API
    url: https://api.rewiringamerica.org/
    type: api
    focus: rebate-aggregator
    priority: medium
    country: US
    requires_api_key: false
```

---

## Implementation Notes

### Licensing & ToS

**US Government Sources:**
- All `.gov` sources are public domain or have permissive licensing
- IRS, Grants.gov, HUD, Benefits.gov: Official use permitted
- Attribution recommended for government data

**Korean Government Sources:**
- Government APIs are freely available for public use
- Commercial use may require separate application approval
- Data.go.kr APIs have documented usage policies

**Third-Party APIs:**
- DSIRE API: Requires paid subscription for full access
- Rewiring America: Free public API
- EcoRebates: Commercial API, requires license

### Rate Limiting & Best Practices

1. **API Key Management**: Store API keys securely in environment variables
2. **Caching**: Implement caching to respect rate limits
3. **Pagination**: Use proper pagination for large datasets
4. **Error Handling**: Implement retry logic with exponential backoff
5. **User Agents**: Set appropriate User-Agent headers for all requests

### Data Validation

1. **RSS Feed Validation**: Verify XML/RSS structure before parsing
2. **API Response Validation**: Check for expected data format
3. **Scraping Robustness**: Handle page structure changes gracefully
4. **Timestamp Tracking**: Maintain last fetched timestamps for incremental updates

---

## Summary

**Total Sources Identified:**
- RSS Feeds: 16+ sources
- APIs: 10+ endpoints
- Scraping Targets: 13+ websites
- Geographic Coverage: United States (federal + state) and South Korea

**Recommendation Priority:**
1. Start with US government official sources (IRS, Grants.gov, HUD, Benefits.gov)
2. Add Korean government sources for local relevance
3. Include energy rebate aggregators (DSIRE, Energy Star)
4. Implement caching for all high-frequency sources
5. Monitor rate limits and implement backoff strategies

**Total Sources**: 16+ RSS, 10+ APIs, 13+ Scraping Targets
