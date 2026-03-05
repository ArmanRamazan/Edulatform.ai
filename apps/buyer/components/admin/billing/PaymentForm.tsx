"use client";

import { useState, type FormEvent } from "react";
import {
  CardElement,
  useStripe,
  useElements,
} from "@stripe/react-stripe-js";
import type { StripeCardElementChangeEvent } from "@stripe/stripe-js";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const CARD_ELEMENT_OPTIONS = {
  style: {
    base: {
      color: "#e2e8f0",
      fontFamily: "Inter, system-ui, sans-serif",
      fontSize: "16px",
      "::placeholder": { color: "#64748b" },
      iconColor: "#7c5cfc",
    },
    invalid: {
      color: "#ef4444",
      iconColor: "#ef4444",
    },
  },
};

interface PaymentFormProps {
  planTier: string;
  orgEmail: string;
  orgName: string;
  onSuccess: (paymentMethodId: string) => void;
  isSubmitting: boolean;
}

export function PaymentForm({
  planTier,
  orgEmail,
  orgName,
  onSuccess,
  isSubmitting,
}: PaymentFormProps) {
  const stripe = useStripe();
  const elements = useElements();
  const [error, setError] = useState<string | null>(null);
  const [cardComplete, setCardComplete] = useState(false);
  const [processing, setProcessing] = useState(false);

  const handleCardChange = (event: StripeCardElementChangeEvent) => {
    setError(event.error ? event.error.message : null);
    setCardComplete(event.complete);
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!stripe || !elements) return;

    setProcessing(true);
    setError(null);

    const cardElement = elements.getElement(CardElement);
    if (!cardElement) {
      setError("Card element not found");
      setProcessing(false);
      return;
    }

    const { error: pmError, paymentMethod } =
      await stripe.createPaymentMethod({
        type: "card",
        card: cardElement,
        billing_details: { email: orgEmail },
      });

    if (pmError) {
      setError(pmError.message ?? "Payment failed");
      setProcessing(false);
      return;
    }

    if (paymentMethod) {
      onSuccess(paymentMethod.id);
    }
    setProcessing(false);
  };

  const busy = processing || isSubmitting;

  return (
    <Card className="border-border/50">
      <CardHeader>
        <CardTitle className="text-base">Payment Details</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="rounded-md border border-border/50 bg-background/50 p-3">
            <CardElement
              options={CARD_ELEMENT_OPTIONS}
              onChange={handleCardChange}
            />
          </div>

          {error && (
            <p className="text-sm text-destructive">{error}</p>
          )}

          <div className="text-xs text-muted-foreground">
            Subscribing to{" "}
            <span className="font-semibold capitalize text-foreground">
              {planTier}
            </span>{" "}
            plan for <span className="font-semibold text-foreground">{orgName}</span>
          </div>

          <Button
            type="submit"
            disabled={!stripe || !cardComplete || busy}
            className="w-full bg-[#7c5cfc] hover:bg-[#6a4de6]"
          >
            {busy ? "Processing..." : "Subscribe"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
