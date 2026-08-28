import { useState } from "react";
import { StatusBar } from "expo-status-bar";
import {
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";

type Tab = "home" | "scan" | "rrg" | "orders";

const colors = {
  bg: "#08111f",
  panel: "#0e1b2c",
  panelLight: "#13263c",
  line: "#203650",
  text: "#e4eef9",
  muted: "#7b92ad",
  blue: "#58adff",
  green: "#45d39c",
  purple: "#a08eff",
  orange: "#f5a45b",
  red: "#ed6a85",
};

const quotes = [
  { symbol: "RELIANCE", price: "₹2,942.40", change: "+1.84%", signal: "Momentum", color: colors.green },
  { symbol: "SUNPHARMA", price: "₹1,742.30", change: "+2.32%", signal: "Momentum", color: colors.green },
  { symbol: "ICICIBANK", price: "₹1,328.65", change: "+1.25%", signal: "Momentum", color: colors.green },
  { symbol: "TCS", price: "₹4,120.75", change: "-0.22%", signal: "Watch", color: colors.orange },
];

export default function App() {
  const [tab, setTab] = useState<Tab>("home");

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar style="light" />
      <View style={styles.header}>
        <View style={styles.logo}><Text style={styles.logoText}>A</Text></View>
        <View style={styles.headerTitle}>
          <Text style={styles.title}>ALL IN ONE</Text>
          <Text style={styles.subtitle}>TRADING LAB</Text>
        </View>
        <View style={styles.mode}><View style={styles.dot} /><Text style={styles.modeText}>PAPER</Text></View>
      </View>

      <ScrollView contentContainerStyle={styles.content}>
        {tab === "home" && <HomeScreen onTab={setTab} />}
        {tab === "scan" && <ScanScreen />}
        {tab === "rrg" && <RrgScreen />}
        {tab === "orders" && <OrdersScreen />}
      </ScrollView>

      <View style={styles.bottomNav}>
        <NavButton label="Home" icon="⌂" active={tab === "home"} onPress={() => setTab("home")} />
        <NavButton label="Screener" icon="⌕" active={tab === "scan"} onPress={() => setTab("scan")} />
        <NavButton label="RRG" icon="◎" active={tab === "rrg"} onPress={() => setTab("rrg")} />
        <NavButton label="Paper book" icon="▤" active={tab === "orders"} onPress={() => setTab("orders")} />
      </View>
    </SafeAreaView>
  );
}

function HomeScreen({ onTab }: { onTab: (tab: Tab) => void }) {
  return (
    <>
      <Text style={styles.eyebrow}>FRIDAY · 28 AUG 2026</Text>
      <Text style={styles.heading}>Good morning, Rahul.</Text>
      <Text style={styles.body}>Your private research workspace is ready.</Text>

      <View style={styles.cards}>
        <Metric label="Paper capital" value="₹1,00,000" detail="Available" />
        <Metric label="Today’s move" value="+₹2,480" detail="Simulated" positive />
      </View>

      <View style={styles.sectionHeader}><Text style={styles.sectionTitle}>Market pulse</Text><Text style={styles.link}>NIFTY 50 · 1D</Text></View>
      <View style={styles.chartCard}>
        <Text style={styles.chartValue}>24,548.70</Text>
        <Text style={styles.positive}>+0.84% today</Text>
        <View style={styles.chart}><View style={styles.chartLine} /><View style={styles.chartLineTwo} /></View>
        <View style={styles.chartLabels}><Text>01 Aug</Text><Text>15 Aug</Text><Text>28 Aug</Text></View>
      </View>

      <View style={styles.sectionHeader}><Text style={styles.sectionTitle}>Saved momentum scan</Text><Pressable onPress={() => onTab("scan")}><Text style={styles.link}>Open →</Text></Pressable></View>
      <View style={styles.listCard}>
        {quotes.map((quote) => <QuoteRow key={quote.symbol} {...quote} />)}
      </View>

      <Pressable style={styles.primary} onPress={() => onTab("scan")}><Text style={styles.primaryText}>Run screener</Text><Text style={styles.primaryArrow}>→</Text></Pressable>
    </>
  );
}

function ScanScreen() {
  return (
    <>
      <Text style={styles.eyebrow}>RULE BUILDER</Text>
      <Text style={styles.heading}>Market screener</Text>
      <Text style={styles.body}>Chartink-style conditions for your private watchlists.</Text>
      <View style={styles.formCard}>
        <Field label="Universe" value="NIFTY 50" />
        <Field label="Timeframe" value="Daily" />
        <Text style={styles.matchLabel}>MATCH ALL CONDITIONS</Text>
        <Condition field="RSI (14)" operator=">" value="50" />
        <Condition field="Change %" operator=">" value="0" />
        <Condition field="Volume" operator=">" value="1,000,000" />
        <Pressable style={styles.addButton}><Text style={styles.addText}>＋ Add condition</Text></Pressable>
      </View>
      <View style={styles.sectionHeader}><Text style={styles.sectionTitle}>8 matches</Text><Text style={styles.link}>Demo feed</Text></View>
      <View style={styles.listCard}>{quotes.map((quote) => <QuoteRow key={quote.symbol} {...quote} />)}</View>
      <View style={styles.warning}><Text style={styles.warningIcon}>!</Text><Text style={styles.warningText}>SmartAPI is not connected in this preview. Results are demo data and cannot place orders.</Text></View>
    </>
  );
}

function RrgScreen() {
  return (
    <>
      <Text style={styles.eyebrow}>RELATIVE ROTATION · 20 BARS</Text>
      <Text style={styles.heading}>RRG radar</Text>
      <Text style={styles.body}>Leadership rotation across NIFTY 50.</Text>
      <View style={styles.rrgCard}>
        <View style={styles.quad topLeft}><Text style={styles.quadBlue}>IMPROVING</Text></View>
        <View style={styles.quad topRight}><Text style={styles.quadGreen}>LEADING</Text></View>
        <View style={styles.quad bottomLeft}><Text style={styles.quadRed}>LAGGING</Text></View>
        <View style={styles.quad bottomRight}><Text style={styles.quadOrange}>WEAKENING</Text></View>
        <View style={styles.crossVertical} /><View style={styles.crossHorizontal} />
        <View style={[styles.rrgPoint, { left: "68%", top: "26%", backgroundColor: colors.green }]}><Text style={styles.pointText}>RE</Text></View>
        <View style={[styles.rrgPoint, { left: "58%", top: "34%", backgroundColor: colors.green }]}><Text style={styles.pointText}>IC</Text></View>
        <View style={[styles.rrgPoint, { left: "32%", top: "39%", backgroundColor: colors.blue }]}><Text style={styles.pointText}>BH</Text></View>
        <View style={[styles.rrgPoint, { left: "37%", top: "67%", backgroundColor: colors.red }]}><Text style={styles.pointText}>TC</Text></View>
      </View>
      <Text style={styles.sectionTitle}>Rotation table</Text>
      <View style={styles.listCard}>{["RELIANCE", "ICICIBANK", "BHARTIARTL", "TCS"].map((symbol, index) => <View style={styles.rotationRow} key={symbol}><View style={[styles.smallDot, { backgroundColor: [colors.green, colors.green, colors.blue, colors.red][index] }]} /><Text style={styles.rowSymbol}>{symbol}</Text><Text style={styles.rowValue}>{["Leading", "Leading", "Improving", "Lagging"][index]}</Text></View>)}</View>
    </>
  );
}

function OrdersScreen() {
  return (
    <>
      <Text style={styles.eyebrow}>PAPER LEDGER</Text>
      <Text style={styles.heading}>Order review</Text>
      <Text style={styles.body}>Every trade remains simulated until live execution is explicitly enabled.</Text>
      <View style={styles.orderCard}><Text style={styles.orderLabel}>RELIANCE · MIS</Text><Text style={styles.orderTitle}>Buy 10 shares at ₹2,942.40</Text><View style={styles.orderGrid}><Field label="Margin" value="₹5,884.80" /><Field label="Charges est." value="₹18.42" /></View><View style={styles.orderButtons}><Pressable style={styles.secondary}><Text style={styles.secondaryText}>Edit</Text></Pressable><Pressable style={styles.primarySmall}><Text style={styles.primaryText}>Paper order</Text></Pressable></View></View>
      <View style={styles.warning}><Text style={styles.warningIcon}>✓</Text><Text style={styles.warningText}>Live trading is disabled. Broker calculations will be verified before any execution adapter is added.</Text></View>
    </>
  );
}

function Metric({ label, value, detail, positive }: { label: string; value: string; detail: string; positive?: boolean }) {
  return <View style={styles.metric}><Text style={styles.metricLabel}>{label}</Text><Text style={[styles.metricValue, positive && styles.positive]}>{value}</Text><Text style={styles.metricDetail}>{detail}</Text></View>;
}

function QuoteRow({ symbol, price, change, signal, color }: { symbol: string; price: string; change: string; signal: string; color: string }) {
  return <View style={styles.quoteRow}><View style={[styles.symbolIcon, { backgroundColor: color + "22" }]}><Text style={[styles.symbolIconText, { color }]}>{symbol.slice(0, 2)}</Text></View><View style={styles.quoteName}><Text style={styles.rowSymbol}>{symbol}</Text><Text style={styles.rowSub}>{signal}</Text></View><View><Text style={styles.rowPrice}>{price}</Text><Text style={[styles.rowValue, { color }]}>{change}</Text></View></View>;
}

function Field({ label, value }: { label: string; value: string }) {
  return <View style={styles.field}><Text style={styles.fieldLabel}>{label}</Text><View style={styles.fieldValue}><Text style={styles.fieldText}>{value}</Text><Text style={styles.chevron}>⌄</Text></View></View>;
}

function Condition({ field, operator, value }: { field: string; operator: string; value: string }) {
  return <View style={styles.condition}><Text style={styles.conditionNumber}>•</Text><Text style={styles.conditionField}>{field}</Text><Text style={styles.conditionOperator}>{operator}</Text><Text style={styles.conditionValue}>{value}</Text></View>;
}

function NavButton({ label, icon, active, onPress }: { label: string; icon: string; active: boolean; onPress: () => void }) {
  return <Pressable style={styles.navButton} onPress={onPress}><Text style={[styles.navIcon, active && styles.navActive]}>{icon}</Text><Text style={[styles.navLabel, active && styles.navActive]}>{label}</Text></Pressable>;
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  header: { height: 70, paddingHorizontal: 18, flexDirection: "row", alignItems: "center", borderBottomWidth: 1, borderBottomColor: colors.line },
  logo: { width: 33, height: 33, borderRadius: 10, backgroundColor: colors.blue, alignItems: "center", justifyContent: "center" },
  logoText: { color: colors.bg, fontSize: 20, fontWeight: "800" },
  headerTitle: { marginLeft: 10 },
  title: { color: colors.text, fontSize: 11, fontWeight: "800", letterSpacing: 2 },
  subtitle: { color: colors.muted, fontSize: 8, letterSpacing: 2, marginTop: 3 },
  mode: { marginLeft: "auto", flexDirection: "row", alignItems: "center", gap: 6, backgroundColor: "#12382f", paddingHorizontal: 9, paddingVertical: 6, borderRadius: 12 },
  dot: { width: 6, height: 6, borderRadius: 4, backgroundColor: colors.green },
  modeText: { color: colors.green, fontSize: 9, fontWeight: "700" },
  content: { padding: 20, paddingBottom: 35 },
  eyebrow: { color: "#6f88a5", fontSize: 9, letterSpacing: 1.5, fontWeight: "700", marginTop: 8 },
  heading: { color: colors.text, fontSize: 28, fontWeight: "700", marginTop: 7, letterSpacing: -0.7 },
  body: { color: colors.muted, fontSize: 12, lineHeight: 19, marginTop: 6, marginBottom: 22 },
  cards: { flexDirection: "row", gap: 9, marginBottom: 25 },
  metric: { flex: 1, backgroundColor: colors.panel, borderColor: colors.line, borderWidth: 1, borderRadius: 11, padding: 14 },
  metricLabel: { color: colors.muted, fontSize: 10 },
  metricValue: { color: colors.text, fontWeight: "700", fontSize: 18, marginTop: 7 },
  metricDetail: { color: "#5e7897", fontSize: 9, marginTop: 5 },
  positive: { color: colors.green },
  sectionHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 10, marginTop: 5 },
  sectionTitle: { color: colors.text, fontSize: 15, fontWeight: "650", marginBottom: 10 },
  link: { color: colors.blue, fontSize: 10 },
  chartCard: { backgroundColor: colors.panel, borderColor: colors.line, borderWidth: 1, borderRadius: 11, padding: 16, marginBottom: 24 },
  chartValue: { color: colors.text, fontSize: 24, fontWeight: "700" },
  chart: { height: 125, marginTop: 15, overflow: "hidden", position: "relative", borderBottomWidth: 1, borderBottomColor: colors.line },
  chartLine: { position: "absolute", left: -15, top: 50, width: 390, height: 100, borderTopWidth: 3, borderTopColor: colors.blue, transform: [{ rotate: "-12deg" }] },
  chartLineTwo: { position: "absolute", left: -15, top: 78, width: 390, height: 100, borderTopWidth: 2, borderTopColor: colors.purple, transform: [{ rotate: "-8deg" }] },
  chartLabels: { flexDirection: "row", justifyContent: "space-between", marginTop: 7 },
  chartLabelsText: { color: colors.muted, fontSize: 9 },
  listCard: { backgroundColor: colors.panel, borderColor: colors.line, borderWidth: 1, borderRadius: 11, paddingHorizontal: 14, marginBottom: 18 },
  quoteRow: { flexDirection: "row", alignItems: "center", paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: "#16283d" },
  symbolIcon: { width: 31, height: 31, borderRadius: 8, alignItems: "center", justifyContent: "center" },
  symbolIconText: { fontSize: 9, fontWeight: "800" },
  quoteName: { flex: 1, marginLeft: 10 },
  rowSymbol: { color: "#d2e1ef", fontSize: 11, fontWeight: "600" },
  rowSub: { color: colors.muted, fontSize: 9, marginTop: 4 },
  rowPrice: { color: "#c8d8e8", fontSize: 10, textAlign: "right" },
  rowValue: { fontSize: 9, marginTop: 4, textAlign: "right" },
  primary: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 12, backgroundColor: colors.blue, padding: 13, borderRadius: 8 },
  primarySmall: { flex: 1, alignItems: "center", backgroundColor: colors.blue, padding: 12, borderRadius: 8 },
  primaryText: { color: colors.bg, fontSize: 11, fontWeight: "700" },
  primaryArrow: { color: colors.bg, fontSize: 17 },
  formCard: { backgroundColor: colors.panel, borderColor: colors.line, borderWidth: 1, borderRadius: 11, padding: 15, marginBottom: 23 },
  field: { marginBottom: 12, flex: 1 },
  fieldLabel: { color: colors.muted, fontSize: 9, marginBottom: 6 },
  fieldValue: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", backgroundColor: "#0a1727", borderColor: "#27415c", borderWidth: 1, borderRadius: 6, padding: 10 },
  fieldText: { color: "#c8d9eb", fontSize: 10 },
  chevron: { color: colors.muted, fontSize: 13 },
  matchLabel: { color: "#6f88a5", fontSize: 9, letterSpacing: 1, marginTop: 5, marginBottom: 5 },
  condition: { flexDirection: "row", alignItems: "center", backgroundColor: "#102238", borderRadius: 6, padding: 11, marginTop: 6, gap: 7 },
  conditionNumber: { color: colors.blue, fontSize: 12 },
  conditionField: { flex: 1, color: "#c9daeb", fontSize: 10 },
  conditionOperator: { color: colors.purple, fontWeight: "700", fontSize: 11 },
  conditionValue: { color: colors.text, fontSize: 10, fontWeight: "600" },
  addButton: { alignItems: "center", borderColor: "#315575", borderWidth: 1, borderStyle: "dashed", borderRadius: 6, padding: 10, marginTop: 10 },
  addText: { color: colors.blue, fontSize: 10 },
  warning: { flexDirection: "row", gap: 9, backgroundColor: "#2b241b", borderColor: "#5a472a", borderWidth: 1, borderRadius: 7, padding: 11, marginTop: 8 },
  warningIcon: { color: colors.orange, fontWeight: "800", fontSize: 14 },
  warningText: { flex: 1, color: "#c5a875", fontSize: 9, lineHeight: 15 },
  rrgCard: { height: 350, borderWidth: 1, borderColor: colors.line, borderRadius: 11, backgroundColor: colors.panel, position: "relative", overflow: "hidden", marginBottom: 23 },
  quad: { position: "absolute", width: "50%", height: "50%", padding: 13 },
  topLeft: { left: 0, top: 0, backgroundColor: "#102840" },
  topRight: { right: 0, top: 0, backgroundColor: "#12352f" },
  bottomLeft: { left: 0, bottom: 0, backgroundColor: "#321d29" },
  bottomRight: { right: 0, bottom: 0, backgroundColor: "#3a2b20" },
  quadBlue: { color: colors.blue, fontSize: 8, fontWeight: "700" },
  quadGreen: { color: colors.green, fontSize: 8, fontWeight: "700", textAlign: "right" },
  quadRed: { color: colors.red, fontSize: 8, fontWeight: "700" },
  quadOrange: { color: colors.orange, fontSize: 8, fontWeight: "700", textAlign: "right" },
  crossVertical: { position: "absolute", top: 0, bottom: 0, left: "50%", borderLeftWidth: 1, borderStyle: "dashed", borderColor: "#58718b" },
  crossHorizontal: { position: "absolute", left: 0, right: 0, top: "50%", borderTopWidth: 1, borderStyle: "dashed", borderColor: "#58718b" },
  rrgPoint: { position: "absolute", width: 27, height: 27, borderRadius: 18, alignItems: "center", justifyContent: "center", borderWidth: 2, borderColor: "#dcefff" },
  pointText: { color: colors.bg, fontSize: 8, fontWeight: "800" },
  rotationRow: { flexDirection: "row", alignItems: "center", paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: "#16283d" },
  smallDot: { width: 7, height: 7, borderRadius: 5, marginRight: 10 },
  orderCard: { backgroundColor: colors.panel, borderColor: colors.line, borderWidth: 1, borderRadius: 11, padding: 16, marginTop: 6, marginBottom: 18 },
  orderLabel: { color: colors.blue, fontSize: 9, letterSpacing: 1.2, fontWeight: "700" },
  orderTitle: { color: colors.text, fontSize: 16, fontWeight: "600", marginTop: 9, marginBottom: 18 },
  orderGrid: { flexDirection: "row", gap: 10 },
  orderButtons: { flexDirection: "row", gap: 8, marginTop: 8 },
  secondary: { flex: 1, alignItems: "center", borderColor: "#29445f", borderWidth: 1, padding: 11, borderRadius: 8 },
  secondaryText: { color: "#b5cce2", fontSize: 11 },
  bottomNav: { height: 73, borderTopWidth: 1, borderTopColor: colors.line, backgroundColor: "#091523", flexDirection: "row", justifyContent: "space-around", alignItems: "center" },
  navButton: { alignItems: "center", padding: 6, minWidth: 64 },
  navIcon: { color: colors.muted, fontSize: 21, lineHeight: 24 },
  navLabel: { color: colors.muted, fontSize: 9, marginTop: 4 },
  navActive: { color: colors.blue },
});
