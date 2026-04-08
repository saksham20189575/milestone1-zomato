import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { HeroSearch } from "@/components/HeroSearch";

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <main className="flex-1">
        <HeroSearch />
      </main>
      <Footer />
    </div>
  );
}
