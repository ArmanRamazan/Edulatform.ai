import { GraphView } from "@/components/graph/GraphView";

interface GraphPageProps {
  searchParams: Promise<{ courseId?: string }>;
}

/**
 * /graph — knowledge graph full-page view.
 *
 * Accepts ?courseId=<id> query param. The graph canvas occupies the full
 * viewport height minus the 48px TopBar, with no extra padding (negates the
 * (app) layout's p-6 wrapper).
 */
export default async function GraphPage({ searchParams }: GraphPageProps) {
  const { courseId } = await searchParams;

  return (
    // Negate the layout's p-6 so the graph fills edge-to-edge.
    // h-[calc(100vh-48px)] = full viewport minus TopBar height.
    <div className="-m-6 h-[calc(100vh-48px)] overflow-hidden">
      <GraphView courseId={courseId ?? ""} />
    </div>
  );
}
