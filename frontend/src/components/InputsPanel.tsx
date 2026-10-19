import { Accordion, ActionIcon, Button, Card, Collapse, Group, SimpleGrid, Stack, Text,
  Textarea, Tooltip } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";

import type { Inputs } from "../api/client";
import { useInputs, useScenario } from "../state/ScenarioContext";
import { NumField, SelectField, SwitchField, TextField, YearOverrides } from "./fields";

const G = ({ children, cols = 2 }: { children: React.ReactNode; cols?: number }) => (
  <SimpleGrid cols={cols} spacing="xs" verticalSpacing="xs">{children}</SimpleGrid>
);

function Toggle({ label, children }: { label: string; children: React.ReactNode }) {
  const [open, { toggle }] = useDisclosure(false);
  return (
    <div>
      <Button variant="subtle" size="compact-xs" onClick={toggle} px={0}>
        {open ? "▾" : "▸"} {label}
      </Button>
      <Collapse expanded={open}><Stack gap="xs" mt={4}>{children}</Stack></Collapse>
    </div>
  );
}

function ComponentCard({ i }: { i: number }) {
  const inputs = useInputs();
  const { update } = useScenario();
  const c = inputs.components[i];
  const hold = inputs.analysis?.hold_period_years ?? 5;
  const p = (...rest: (string | number)[]) => ["components", i, ...rest];
  return (
    <Card withBorder padding="sm" radius="md">
      <Group justify="space-between" mb="xs">
        <Text fw={600} size="sm">{c.name}</Text>
        {inputs.components.length > 1 && (
          <Tooltip label="Remove component">
            <ActionIcon variant="subtle" color="red" size="sm" aria-label="Remove component"
              onClick={() => update((prev) => ({
                ...prev, components: prev.components.filter((_, j) => j !== i),
              }))}>✕</ActionIcon>
          </Tooltip>
        )}
      </Group>
      <Stack gap="xs">
        <G cols={3}>
          <TextField path={p("name")} label="Name" />
          <SelectField path={p("use_type")} label="Use" data={[
            { value: "office", label: "Office" }, { value: "retail", label: "Retail" }]} />
          <NumField path={p("nla_sqft")} label="NLA (sq ft)" kind="money" min={1} />
        </G>
        <G cols={2}>
          <NumField path={p("revenue", "rent_psf_pm")} label="Rent (psf pm, Year 1)" kind="psf" />
          <NumField path={p("revenue", "rent_growth")} label="Rent growth (pa)" kind="pct" />
          <NumField path={p("revenue", "vacancy")} label="Vacancy" kind="pct" />
          <NumField path={p("revenue", "credit_loss")} label="Credit loss" kind="pct" />
          <NumField path={p("opex_psf_pm")} label="Opex (psf pm)" kind="psf" />
          <NumField path={p("opex_growth")} label="Opex growth" kind="pct" />
          <NumField path={p("recoveries_psf_pm")} label="Recoveries (psf pm)" kind="psf"
            description="Service charge / A&P billed on top" />
          <NumField path={p("turnover_rent_pct")} label="Turnover rent" kind="pct"
            description="% uplift on base rent" />
        </G>
        <Toggle label="Leasing assumptions">
          <G cols={2}>
            <NumField path={p("leasing", "avg_lease_term_years")} label="Avg lease term (yrs)"
              kind="years" />
            <NumField path={p("leasing", "renewal_probability")} label="Renewal probability"
              kind="pct" />
            <NumField path={p("leasing", "rent_free_months_per_year_new")}
              label="Rent-free, new (mths / lease yr)" kind="months" />
            <NumField path={p("leasing", "rent_free_months_per_year_renewal")}
              label="Rent-free, renewal (mths / lease yr)" kind="months" />
            <NumField path={p("leasing", "commission_months_new")} label="Commission, new (mths)"
              kind="months" />
            <NumField path={p("leasing", "commission_months_renewal")}
              label="Commission, renewal (mths)" kind="months" />
            <NumField path={p("leasing", "fitout_contribution_psf_new")}
              label="Fit-out contribution, new ($ psf)" kind="psf" />
          </G>
        </Toggle>
        <Toggle label="Year-by-year overrides">
          <YearOverrides path={p("revenue", "vacancy_overrides")} label="Vacancy"
            years={hold + 1} fallback={c.revenue.vacancy} />
          <YearOverrides path={p("revenue", "rent_growth_overrides")} label="Rent growth"
            years={hold + 1} firstYear={2} fallback={c.revenue.rent_growth} />
        </Toggle>
      </Stack>
    </Card>
  );
}

function OtherIncome() {
  const inputs = useInputs();
  const { update } = useScenario();
  const lines = inputs.other_income ?? [];
  return (
    <Stack gap="xs">
      {lines.map((_, i) => (
        <Group key={i} gap="xs" align="flex-end" wrap="nowrap">
          <div style={{ flex: 2 }}><TextField path={["other_income", i, "name"]} label="Item" /></div>
          <div style={{ flex: 2 }}>
            <NumField path={["other_income", i, "annual_amount"]} label="Year 1 amount" kind="money" />
          </div>
          <div style={{ flex: 1 }}>
            <NumField path={["other_income", i, "growth"]} label="Growth" kind="pct" />
          </div>
          <ActionIcon variant="subtle" color="red" mb={4} aria-label="Remove income line"
            onClick={() => update((prev) => ({
              ...prev, other_income: (prev.other_income ?? []).filter((_, j) => j !== i),
            }))}>✕</ActionIcon>
        </Group>
      ))}
      <Button size="compact-xs" variant="light" w="fit-content" onClick={() => update((prev) => ({
        ...prev,
        other_income: [...(prev.other_income ?? []), { name: "New income", annual_amount: 0, growth: 0.02 }],
      }))}>+ Add income line</Button>
    </Stack>
  );
}

function WaterfallTiers() {
  const inputs = useInputs();
  const { update } = useScenario();
  const tiers = inputs.waterfall.tiers;
  return (
    <Stack gap="xs">
      {tiers.map((_, i) => {
        const last = i === tiers.length - 1;
        return (
          <Group key={i} gap="xs" align="flex-end" wrap="nowrap">
            <Text size="xs" w={52} mb={8}>Tier {i + 1}</Text>
            <div style={{ flex: 1 }}>
              {last ? (
                <Text size="xs" c="dimmed" mb={8}>Above previous hurdle</Text>
              ) : (
                <NumField path={["waterfall", "tiers", i, "up_to_irr"]} label="Up to LP IRR"
                  kind="pct" />
              )}
            </div>
            <div style={{ flex: 1 }}>
              <NumField path={["waterfall", "tiers", i, "gp_promote"]} label="GP promote" kind="pct" />
            </div>
            {tiers.length > 1 && !last && (
              <ActionIcon variant="subtle" color="red" mb={4} aria-label="Remove tier"
                onClick={() => update((prev) => ({
                  ...prev,
                  waterfall: { ...prev.waterfall, tiers: prev.waterfall.tiers.filter((_, j) => j !== i) },
                }))}>✕</ActionIcon>
            )}
          </Group>
        );
      })}
      <Button size="compact-xs" variant="light" w="fit-content" onClick={() => update((prev) => {
        const ts = prev.waterfall.tiers;
        const bounded = ts.filter((x) => x.up_to_irr != null);
        const lastHurdle = bounded.length ? bounded[bounded.length - 1].up_to_irr! : prev.waterfall.pref_rate;
        const newTier = { up_to_irr: Number((lastHurdle + 0.03).toFixed(4)), gp_promote: ts[ts.length - 1].gp_promote };
        return { ...prev, waterfall: { ...prev.waterfall, tiers: [...ts.slice(0, -1), newTier, ts[ts.length - 1]] } };
      })}>+ Add tier</Button>
    </Stack>
  );
}

export function InputsPanel() {
  const inputs = useInputs();
  const { update, setField } = useScenario();
  const hold = inputs.analysis?.hold_period_years ?? 5;
  const addComponent = () => update((prev: Inputs) => {
    const src = prev.components[prev.components.length - 1];
    return { ...prev, components: [...prev.components,
      { ...structuredClone(src), name: `${src.name} ${prev.components.length + 1}` }] };
  });

  return (
    <Accordion multiple defaultValue={["deal", "components"]} variant="separated" radius="md">
      <Accordion.Item value="deal">
        <Accordion.Control>Scenario & property</Accordion.Control>
        <Accordion.Panel>
          <Stack gap="xs">
            <TextField path={["scenario", "name"]} label="Scenario name" />
            <Textarea size="xs" label="Description" autosize minRows={1} maxRows={4}
              value={inputs.scenario.description ?? ""}
              onChange={(e) => setField(["scenario", "description"], e.currentTarget.value)} />
            <G>
              <TextField path={["property", "name"]} label="Property" />
              <TextField path={["property", "submarket"]} label="Submarket" />
              <SelectField path={["property", "tenure"]} label="Tenure" data={[
                { value: "leasehold", label: "Leasehold" }, { value: "freehold", label: "Freehold" }]} />
              <NumField path={["property", "lease_years_remaining"]} label="Lease years remaining"
                kind="years" nullable />
              <NumField path={["analysis", "start_year"]} label="First year (Year 1)" kind="int" />
              <NumField path={["analysis", "hold_period_years"]} label="Hold period (yrs)" kind="int"
                min={1} max={30} />
              <NumField path={["analysis", "discount_rate"]} label="Discount rate (NPV)" kind="pct" />
              <TextField path={["analysis", "currency"]} label="Currency" />
            </G>
          </Stack>
        </Accordion.Panel>
      </Accordion.Item>

      <Accordion.Item value="components">
        <Accordion.Control>Space components ({inputs.components.length})</Accordion.Control>
        <Accordion.Panel>
          <Stack gap="sm">
            {inputs.components.map((_, i) => <ComponentCard key={i} i={i} />)}
            <Button size="compact-xs" variant="light" w="fit-content" onClick={addComponent}>
              + Add component
            </Button>
          </Stack>
        </Accordion.Panel>
      </Accordion.Item>

      <Accordion.Item value="income">
        <Accordion.Control>Other income</Accordion.Control>
        <Accordion.Panel><OtherIncome /></Accordion.Panel>
      </Accordion.Item>

      <Accordion.Item value="acq">
        <Accordion.Control>Acquisition</Accordion.Control>
        <Accordion.Panel>
          <G>
            <NumField path={["acquisition", "purchase_price"]} label="Purchase price" kind="money" />
            <SelectField path={["acquisition", "deal_structure"]} label="Deal structure" data={[
              { value: "asset", label: "Asset deal (BSD tiers)" },
              { value: "share", label: "Share deal (0.2% duty)" }]} />
            <NumField path={["acquisition", "stamp_duty_override_pct"]} label="Stamp duty override"
              kind="pct" nullable placeholder="calculated" />
            <NumField path={["acquisition", "other_costs_pct"]} label="Other costs" kind="pct" />
            <NumField path={["acquisition", "upfront_capex"]} label="Upfront capex" kind="money" />
          </G>
        </Accordion.Panel>
      </Accordion.Item>

      <Accordion.Item value="opex">
        <Accordion.Control>Property expenses</Accordion.Control>
        <Accordion.Panel>
          <G>
            <NumField path={["expenses", "property_tax_rate"]} label="Property tax rate" kind="pct" />
            <NumField path={["expenses", "annual_value_year1"]} label="Annual Value, Year 1 (IRAS)"
              kind="money" nullable placeholder="estimate from GPR" />
            <NumField path={["expenses", "av_to_gpr_ratio"]} label="AV / GPR ratio" kind="pct" />
            <NumField path={["expenses", "management_fee_pct"]} label="Property mgmt fee (% EGI)"
              kind="pct" />
            <NumField path={["expenses", "insurance_annual"]} label="Insurance (Year 1)" kind="money" />
            <NumField path={["expenses", "insurance_growth"]} label="Insurance growth" kind="pct" />
          </G>
        </Accordion.Panel>
      </Accordion.Item>

      <Accordion.Item value="capex">
        <Accordion.Control>Capex</Accordion.Control>
        <Accordion.Panel>
          <Stack gap="xs">
            <G>
              <NumField path={["capex", "reserve_psf_pa"]} label="Reserve ($ psf pa)" kind="psf" />
              <NumField path={["capex", "reserve_growth"]} label="Reserve growth" kind="pct" />
            </G>
            <YearOverrides path={["capex", "one_off"]} label="One-off capex by year" years={hold}
              fallback={0} kind="money" />
          </Stack>
        </Accordion.Panel>
      </Accordion.Item>

      <Accordion.Item value="debt">
        <Accordion.Control>Debt</Accordion.Control>
        <Accordion.Panel>
          <Stack gap="xs">
            <SwitchField path={["debt", "enabled"]} label="Use senior debt" />
            <G>
              <NumField path={["debt", "target_ltv"]} label="Target LTV" kind="pct" />
              <NumField path={["debt", "min_dscr"]} label="Min DSCR (sizing)" kind="ratio" nullable />
              <NumField path={["debt", "min_debt_yield"]} label="Min debt yield" kind="pct" nullable />
              <NumField path={["debt", "upfront_fee_pct"]} label="Upfront fee" kind="pct" />
              <NumField path={["debt", "base_rate"]} label="Base rate (SORA)" kind="pct" />
              <NumField path={["debt", "margin"]} label="Margin" kind="pct" />
              <NumField path={["debt", "io_years"]} label="Interest-only years" kind="int" min={0} />
              <NumField path={["debt", "amortization_years"]} label="Amortisation years (0 = IO)"
                kind="int" min={0} />
            </G>
            <YearOverrides path={["debt", "base_rate_overrides"]} label="Base rate by year"
              years={hold} fallback={inputs.debt?.base_rate ?? 0.02} />
          </Stack>
        </Accordion.Panel>
      </Accordion.Item>

      <Accordion.Item value="exit">
        <Accordion.Control>Exit</Accordion.Control>
        <Accordion.Panel>
          <G>
            <NumField path={["exit", "exit_cap_rate"]} label="Exit cap rate" kind="pct" />
            <NumField path={["exit", "selling_cost_pct"]} label="Selling costs" kind="pct" />
            <SelectField path={["exit", "noi_basis"]} label="NOI basis" data={[
              { value: "forward", label: "Forward (Year N+1)" },
              { value: "trailing", label: "Trailing (Year N)" }]} />
          </G>
        </Accordion.Panel>
      </Accordion.Item>

      <Accordion.Item value="fees">
        <Accordion.Control>Fund fees</Accordion.Control>
        <Accordion.Panel>
          <Stack gap="xs">
            <SwitchField path={["fees", "enabled"]} label="Charge fund fees" />
            <G>
              <NumField path={["fees", "asset_mgmt_fee_pct"]} label="Asset mgmt fee (pa)" kind="pct" />
              <SelectField path={["fees", "asset_mgmt_fee_basis"]} label="AM fee basis" data={[
                { value: "gav", label: "Gross asset value" },
                { value: "purchase_price", label: "Purchase price" },
                { value: "equity", label: "Equity" }]} />
              <NumField path={["fees", "acquisition_fee_pct"]} label="Acquisition fee" kind="pct" />
              <NumField path={["fees", "divestment_fee_pct"]} label="Divestment fee" kind="pct" />
            </G>
          </Stack>
        </Accordion.Panel>
      </Accordion.Item>

      <Accordion.Item value="waterfall">
        <Accordion.Control>Equity waterfall</Accordion.Control>
        <Accordion.Panel>
          <Stack gap="xs">
            <SwitchField path={["waterfall", "enabled"]} label="Apply LP/GP waterfall" />
            <G>
              <NumField path={["waterfall", "gp_coinvest_pct"]} label="GP co-invest" kind="pct" />
              <NumField path={["waterfall", "pref_rate"]} label="LP preferred return" kind="pct" />
            </G>
            <WaterfallTiers />
          </Stack>
        </Accordion.Panel>
      </Accordion.Item>
    </Accordion>
  );
}
