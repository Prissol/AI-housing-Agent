import FeaturesSection from "../components/landing/FeaturesSection";
import FinalCtaSection from "../components/landing/FinalCtaSection";
import HeroSection from "../components/landing/HeroSection";
import HowItWorksSection from "../components/landing/HowItWorksSection";
import LandingFooter from "../components/landing/LandingFooter";
import LandingNavbar from "../components/landing/LandingNavbar";
import SecuritySection from "../components/landing/SecuritySection";
import TestimonialsSection from "../components/landing/TestimonialsSection";
import WhyChooseSection from "../components/landing/WhyChooseSection";

function LandingPage() {
  return (
    <div className="text-slate-900">
      <LandingNavbar />
      <main>
        <HeroSection />
        <FeaturesSection />
        <HowItWorksSection />
        <WhyChooseSection />
        <SecuritySection />
        <TestimonialsSection />
        <FinalCtaSection />
      </main>
      <LandingFooter />
    </div>
  );
}

export default LandingPage;
