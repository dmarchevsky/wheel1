'use client';

import React, { useState } from 'react';
import {
  CardHeader,
  CardContent,
  Collapse,
  IconButton,
  Typography,
  Box,
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
} from '@mui/icons-material';
import BaseCard, { BaseCardProps } from './BaseCard';

export interface ExpandableCardProps extends BaseCardProps {
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  action?: React.ReactNode;
  defaultExpanded?: boolean;
  onExpandChange?: (expanded: boolean) => void;
  expandIcon?: React.ReactNode;
  collapsedHeight?: number;
}

export default function ExpandableCard({
  title,
  subtitle,
  action,
  defaultExpanded = true,
  onExpandChange,
  expandIcon,
  collapsedHeight,
  children,
  ...cardProps
}: ExpandableCardProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  const handleExpandClick = () => {
    const newExpanded = !expanded;
    setExpanded(newExpanded);
    onExpandChange?.(newExpanded);
  };

  const renderAction = () => {
    const expandButton = (
      <IconButton
        onClick={handleExpandClick}
        aria-expanded={expanded}
        aria-label="expand"
        size="small"
        sx={{ borderRadius: 0 }}
      >
        {expandIcon || (expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />)}
      </IconButton>
    );

    if (action) {
      return (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {action}
          {expandButton}
        </Box>
      );
    }

    return expandButton;
  };

  return (
    <BaseCard {...cardProps}>
      <CardHeader
        title={
          typeof title === 'string' ? (
            <Typography variant="h6" component="h2">
              {title}
            </Typography>
          ) : (
            title
          )
        }
        subheader={subtitle}
        action={renderAction()}
        sx={{
          pb: expanded ? 1 : 0,
        }}
      />
      <Collapse in={expanded} timeout="auto" unmountOnExit>
        <CardContent sx={{ pt: 0 }}>
          {children}
        </CardContent>
      </Collapse>
    </BaseCard>
  );
}