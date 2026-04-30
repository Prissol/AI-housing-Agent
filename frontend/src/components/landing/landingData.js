import {
  FiActivity,
  FiAlertTriangle,
  FiAward,
  FiCheckCircle,
  FiClock,
  FiFileText,
  FiFolder,
  FiGitMerge,
  FiLock,
  FiMap,
  FiSearch,
  FiShield,
  FiUploadCloud,
  FiUsers,
} from "react-icons/fi";

export const navItems = [
  { label: "Features", href: "#features" },
  { label: "How it works", href: "#how-it-works" },
  { label: "Security", href: "#security" },
  { label: "Contact", href: "#contact" },
];

export const trustLogos = [
  "Urban Planning Authority",
  "Metro Architecture Group",
  "Civic Build Council",
  "Regional Housing Board",
  "Smart Cities Office",
];

export const features = [
  {
    icon: FiMap,
    title: "Map Tracking",
    description: "Monitor every uploaded drawing with status visibility across teams and projects.",
  },
  {
    icon: FiSearch,
    title: "By-law Rule Validation",
    description: "RAG-grounded checks compare plans against zoning and building by-laws instantly.",
  },
  {
    icon: FiAlertTriangle,
    title: "Violation Detection",
    description: "Surface high-risk violations with clear reasoning and confidence context.",
  },
  {
    icon: FiCheckCircle,
    title: "Non-violation Justification",
    description: "Document why a map is compliant using verifiable rule references.",
  },
  {
    icon: FiUsers,
    title: "Team Collaboration",
    description: "Assign reviews, share findings, and keep approvals aligned in one workspace.",
  },
  {
    icon: FiFileText,
    title: "Audit Trail & Reports",
    description: "Export decision-ready reports with complete compliance history and evidence.",
  },
];

export const workflowSteps = [
  {
    icon: FiUploadCloud,
    title: "Upload map files",
    description: "Submit site plans, drawings, and supporting files in one secure intake flow.",
  },
  {
    icon: FiFolder,
    title: "RAG validates by-laws",
    description: "The engine retrieves relevant regulations and evaluates each plan clause-by-clause.",
  },
  {
    icon: FiActivity,
    title: "AI marks findings",
    description: "Violations and non-violations are annotated with legal-style rationale and confidence.",
  },
  {
    icon: FiGitMerge,
    title: "Export and review",
    description: "Generate structured reports and complete team sign-off with a tracked audit history.",
  },
];

export const metrics = [
  {
    value: "72%",
    label: "faster compliance review cycles",
    icon: FiClock,
  },
  {
    value: "43%",
    label: "fewer missed violations in pilot checks",
    icon: FiAward,
  },
  {
    value: "100%",
    label: "documented decisions with supporting rationale",
    icon: FiFileText,
  },
];

export const securityPoints = [
  "Understands huge drawings (image, PDF, DWG/DXF) with smart parsing and fallback analysis",
  "Digitized history for every case with stored extraction, rule evidence, and final report artifacts",
  "Ask-before-answer workflow that blocks low-confidence decisions and requests clarifications",
  "Deterministic bylaw checks so final pass/fail always comes from rule engine, not LLM guessing",
];

export const testimonials = [
  {
    quote:
      "AI Legal Maps helped us standardize compliance reviews across multiple projects without losing legal rigor.",
    name: "Ayesha Khan",
    role: "Senior Planning Manager, UrbanGrid Partners",
  },
  {
    quote:
      "The non-violation explanations are as valuable as violation flags. Stakeholders finally trust the outcomes.",
    name: "Omar Siddiqui",
    role: "Head of Architecture QA, Habitat Studio",
  },
  {
    quote:
      "We cut review bottlenecks dramatically and now produce audit-ready records for every approval cycle.",
    name: "Sara Mahmood",
    role: "Compliance Lead, CivicWorks Advisory",
  },
];
