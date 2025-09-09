'use client'

import { MetricCard, MetricCardProps } from '@/components/ui'

interface SummaryCardProps extends Omit<MetricCardProps, 'variant'> {
  color?: 'primary' | 'success' | 'error' | 'warning' | 'info'
}

export default function SummaryCard(props: SummaryCardProps) {
  return <MetricCard {...props} />
}

