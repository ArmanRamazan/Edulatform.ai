"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import { loadStripe } from "@stripe/stripe-js";
import { Elements } from "@stripe/react-stripe-js";
import {
  CreditCard,
  Users,
  Calendar,
  Crown,
  Building2,
  CheckCircle2,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { useAuth } from "@/hooks/use-auth";
import { useActiveOrg } from "@/hooks/use-active-org";
import {
  useOrgSubscription,
  useCreateOrgSubscription,
  useCancelOrgSubscription,
} from "@/hooks/use-billing";
import type { OrgSubscription } from "@/lib/api";

const PaymentForm = dynamic(
  () =>
    import("@/components/admin/billing/PaymentForm").then(
      (m) => m.PaymentForm,
    ),
  { loading: () => <Skeleton className="h-48 w-full" /> },
);

const stripePromise = process.env.NEXT_PUBLIC_STRIPE_KEY
  ? loadStripe(process.env.NEXT_PUBLIC_STRIPE_KEY)
  : null;

const PLANS = [
  {
    tier: "pilot" as const,
    name: "Pilot",
    price: "$1,000",
    priceCents: 100000,
    seats: 20,
    features: [
      "Up to 20 seats",
      "Knowledge Base ingestion",
      "AI Coach & Missions",
      "Trust Level tracking",
      "Basic analytics",
    ],
  },
  {
    tier: "enterprise" as const,
    name: "Enterprise",
    price: "$10,000",
    priceCents: 1000000,
    seats: 999,
    features: [
      "Up to 999 seats",
      "Everything in Pilot",
      "Priority support",
      "Custom integrations",
      "Advanced analytics & reporting",
      "Dedicated success manager",
    ],
  },
];

function formatDate(iso: string | null): string {
  if (!iso) return "N/A";
  return new Date(iso).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

function statusBadgeVariant(
  status: OrgSubscription["status"],
): "default" | "secondary" | "destructive" {
  switch (status) {
    case "active":
      return "default";
    case "past_due":
      return "secondary";
    case "canceled":
      return "destructive";
  }
}

function CurrentPlanCard({
  subscription,
}: {
  subscription: OrgSubscription;
}) {
  const plan = PLANS.find((p) => p.tier === subscription.plan_tier);

  return (
    <Card className="border-[#7c5cfc]/30">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="flex items-center gap-2 text-lg">
          <Crown className="size-5 text-[#7c5cfc]" />
          Current Plan
        </CardTitle>
        <Badge variant={statusBadgeVariant(subscription.status)}>
          {subscription.status}
        </Badge>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-baseline gap-2">
          <span className="font-mono text-3xl font-bold text-foreground">
            {plan?.name ?? subscription.plan_tier}
          </span>
          <span className="text-muted-foreground">
            {plan?.price ?? `$${(subscription.price_cents / 100).toLocaleString()}`}/mo
          </span>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="flex items-center gap-2 text-sm">
            <Users className="size-4 text-muted-foreground" />
            <span>
              <span className="font-semibold text-foreground">
                {subscription.current_seats}
              </span>
              <span className="text-muted-foreground">
                {" "}
                / {subscription.max_seats} seats
              </span>
            </span>
          </div>

          <div className="flex items-center gap-2 text-sm">
            <Calendar className="size-4 text-muted-foreground" />
            <span className="text-muted-foreground">
              Next billing:{" "}
              <span className="text-foreground">
                {formatDate(subscription.current_period_end)}
              </span>
            </span>
          </div>

          <div className="flex items-center gap-2 text-sm">
            <CreditCard className="size-4 text-muted-foreground" />
            <span className="text-muted-foreground">
              Started:{" "}
              <span className="text-foreground">
                {formatDate(subscription.current_period_start)}
              </span>
            </span>
          </div>

          <div className="flex items-center gap-2 text-sm">
            <Building2 className="size-4 text-muted-foreground" />
            <span className="text-muted-foreground">
              Tier:{" "}
              <span className="font-semibold capitalize text-foreground">
                {subscription.plan_tier}
              </span>
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function PlanComparisonCard({
  currentTier,
  onSelect,
}: {
  currentTier: string | null;
  onSelect: (tier: "pilot" | "enterprise") => void;
}) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {PLANS.map((plan) => {
        const isCurrent = plan.tier === currentTier;
        return (
          <Card
            key={plan.tier}
            className={
              isCurrent
                ? "border-[#7c5cfc]/50 bg-[#7c5cfc]/5"
                : "border-border/50"
            }
          >
            <CardHeader>
              <CardTitle className="flex items-center justify-between text-lg">
                <span>{plan.name}</span>
                {isCurrent && (
                  <Badge variant="default" className="bg-[#7c5cfc]">
                    Current
                  </Badge>
                )}
              </CardTitle>
              <div className="flex items-baseline gap-1">
                <span className="font-mono text-2xl font-bold">
                  {plan.price}
                </span>
                <span className="text-sm text-muted-foreground">/month</span>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <ul className="space-y-2">
                {plan.features.map((feature) => (
                  <li key={feature} className="flex items-start gap-2 text-sm">
                    <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-[#7c5cfc]" />
                    <span className="text-muted-foreground">{feature}</span>
                  </li>
                ))}
              </ul>

              {!isCurrent && (
                <Button
                  onClick={() => onSelect(plan.tier)}
                  className="w-full bg-[#7c5cfc] hover:bg-[#6a4de6]"
                >
                  {currentTier ? "Upgrade" : "Get Started"}
                </Button>
              )}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}

export function BillingPage() {
  const { token } = useAuth();
  const { activeOrg } = useActiveOrg();
  const orgId = activeOrg?.id ?? null;

  const {
    data: subscription,
    isLoading,
    error,
  } = useOrgSubscription(token, orgId);
  const createMutation = useCreateOrgSubscription(token);
  const cancelMutation = useCancelOrgSubscription(token, orgId);

  const [selectedTier, setSelectedTier] = useState<
    "pilot" | "enterprise" | null
  >(null);

  const handlePaymentSuccess = (paymentMethodId: string) => {
    if (!selectedTier || !activeOrg) return;
    createMutation.mutate(
      {
        plan_tier: selectedTier,
        payment_method_id: paymentMethodId,
        org_email: activeOrg.slug + "@knowledgeos.io",
        org_name: activeOrg.name,
      },
      { onSuccess: () => setSelectedTier(null) },
    );
  };

  const handleCancel = () => {
    cancelMutation.mutate();
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-40 w-full" />
        <div className="grid gap-4 md:grid-cols-2">
          <Skeleton className="h-64" />
          <Skeleton className="h-64" />
        </div>
      </div>
    );
  }

  const hasSubscription = subscription && !error;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Billing</h1>
        <p className="text-sm text-muted-foreground">
          Manage your organization subscription and payment
        </p>
      </div>

      {hasSubscription && <CurrentPlanCard subscription={subscription} />}

      <div>
        <h2 className="mb-4 text-lg font-semibold">
          {hasSubscription ? "Change Plan" : "Choose a Plan"}
        </h2>
        <PlanComparisonCard
          currentTier={subscription?.plan_tier ?? null}
          onSelect={setSelectedTier}
        />
      </div>

      {selectedTier && stripePromise && (
        <Elements stripe={stripePromise}>
          <PaymentForm
            planTier={selectedTier}
            orgEmail={activeOrg?.slug + "@knowledgeos.io"}
            orgName={activeOrg?.name ?? ""}
            onSuccess={handlePaymentSuccess}
            isSubmitting={createMutation.isPending}
          />
        </Elements>
      )}

      {selectedTier && !stripePromise && (
        <Card className="border-destructive/30">
          <CardContent className="py-4 text-sm text-destructive">
            Stripe is not configured. Set NEXT_PUBLIC_STRIPE_KEY environment
            variable.
          </CardContent>
        </Card>
      )}

      {createMutation.isError && (
        <p className="text-sm text-destructive">
          Failed to create subscription. Please try again.
        </p>
      )}

      {hasSubscription && subscription.status === "active" && (
        <div className="border-t border-border/50 pt-6">
          <h2 className="mb-2 text-lg font-semibold">Danger Zone</h2>
          <p className="mb-4 text-sm text-muted-foreground">
            Canceling your subscription will take effect at the end of the
            current billing period.
          </p>

          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="destructive">Cancel Plan</Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Cancel subscription?</AlertDialogTitle>
                <AlertDialogDescription>
                  Your team will lose access to premium features at the end of
                  the current billing period (
                  {formatDate(subscription.current_period_end)}). This action
                  cannot be undone.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Keep Plan</AlertDialogCancel>
                <AlertDialogAction
                  onClick={handleCancel}
                  className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                >
                  {cancelMutation.isPending
                    ? "Canceling..."
                    : "Yes, Cancel Plan"}
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>

          {cancelMutation.isError && (
            <p className="mt-2 text-sm text-destructive">
              Failed to cancel subscription. Please try again.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
