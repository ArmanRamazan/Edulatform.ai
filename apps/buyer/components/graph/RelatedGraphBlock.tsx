"use client";

import { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import { ChevronDown, ChevronUp } from "lucide-react";
import { motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import type { ConceptData } from "@/lib/api";

const STORAGE_KEY = "concept-hub-related-collapsed";

interface RelatedGraphBlockProps {
  concept: ConceptData;
  allConcepts: ConceptData[];
  index: number;
}

interface NodePosition {
  id: string;
  name: string;
  x: number;
  y: number;
  isCurrent: boolean;
}

interface Edge {
  from: NodePosition;
  to: NodePosition;
}

export function RelatedGraphBlock({
  concept,
  allConcepts,
  index,
}: RelatedGraphBlockProps) {
  const router = useRouter();

  const [collapsed, setCollapsed] = useState(() => {
    if (typeof window === "undefined") return false;
    return localStorage.getItem(STORAGE_KEY) === "true";
  });

  function toggleCollapse() {
    const next = !collapsed;
    setCollapsed(next);
    localStorage.setItem(STORAGE_KEY, String(next));
  }

  const { nodes, edges } = useMemo(() => {
    // Find 1-hop neighbors: prerequisites + dependents
    const prereqIds = new Set(concept.prerequisites);
    const dependentIds = new Set(
      allConcepts
        .filter((c) => c.prerequisites.includes(concept.id))
        .map((c) => c.id),
    );

    const neighborIds = new Set([...prereqIds, ...dependentIds]);
    const neighbors = allConcepts.filter((c) => neighborIds.has(c.id));

    if (neighbors.length === 0) {
      return { nodes: [] as NodePosition[], edges: [] as Edge[] };
    }

    // Layout: current node in center, neighbors in a circle
    const width = 600;
    const height = 200;
    const cx = width / 2;
    const cy = height / 2;

    const currentNode: NodePosition = {
      id: concept.id,
      name: concept.name,
      x: cx,
      y: cy,
      isCurrent: true,
    };

    const angleStep = (2 * Math.PI) / neighbors.length;
    const radius = Math.min(width * 0.35, height * 0.35);

    const neighborNodes: NodePosition[] = neighbors.map((n, i) => {
      const angle = angleStep * i - Math.PI / 2;
      return {
        id: n.id,
        name: n.name,
        x: cx + radius * Math.cos(angle),
        y: cy + radius * Math.sin(angle),
        isCurrent: false,
      };
    });

    const allNodes = [currentNode, ...neighborNodes];

    const graphEdges: Edge[] = neighborNodes.map((n) => ({
      from: currentNode,
      to: n,
    }));

    return { nodes: allNodes, edges: graphEdges };
  }, [concept, allConcepts]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.1 }}
    >
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Related Concepts
          </CardTitle>
          <Button variant="ghost" size="sm" onClick={toggleCollapse} className="h-6 w-6 p-0">
            {collapsed ? <ChevronDown className="size-4" /> : <ChevronUp className="size-4" />}
          </Button>
        </CardHeader>
        {!collapsed && (
          <CardContent>
            {nodes.length === 0 ? (
              <p className="py-4 text-center text-sm text-muted-foreground">
                No related concepts
              </p>
            ) : (
              <svg
                viewBox="0 0 600 200"
                className="h-[200px] w-full"
                role="img"
                aria-label="Related concepts graph"
              >
                {/* Edges */}
                {edges.map((edge, i) => (
                  <line
                    key={i}
                    x1={edge.from.x}
                    y1={edge.from.y}
                    x2={edge.to.x}
                    y2={edge.to.y}
                    stroke="hsl(var(--muted-foreground))"
                    strokeWidth="1.5"
                    strokeOpacity="0.3"
                  />
                ))}

                {/* Nodes */}
                {nodes.map((node) => (
                  <g
                    key={node.id}
                    className={node.isCurrent ? "" : "cursor-pointer"}
                    onClick={() => {
                      if (!node.isCurrent) {
                        router.push(`/graph/${node.id}`);
                      }
                    }}
                  >
                    <circle
                      cx={node.x}
                      cy={node.y}
                      r={node.isCurrent ? 24 : 18}
                      fill={
                        node.isCurrent
                          ? "hsl(var(--primary))"
                          : "hsl(var(--secondary))"
                      }
                      stroke={
                        node.isCurrent
                          ? "hsl(var(--primary))"
                          : "hsl(var(--border))"
                      }
                      strokeWidth="2"
                    />
                    <text
                      x={node.x}
                      y={node.y + (node.isCurrent ? 40 : 34)}
                      textAnchor="middle"
                      fontSize="11"
                      fill="hsl(var(--muted-foreground))"
                      className="pointer-events-none select-none"
                    >
                      {node.name.length > 16
                        ? node.name.slice(0, 14) + "..."
                        : node.name}
                    </text>
                    {node.isCurrent && (
                      <text
                        x={node.x}
                        y={node.y + 4}
                        textAnchor="middle"
                        fontSize="10"
                        fill="hsl(var(--primary-foreground))"
                        className="pointer-events-none select-none font-medium"
                      >
                        You
                      </text>
                    )}
                  </g>
                ))}
              </svg>
            )}
          </CardContent>
        )}
      </Card>
    </motion.div>
  );
}
