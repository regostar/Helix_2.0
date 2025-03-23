import React from 'react';
import { Box, Card, CardContent, Typography, Stepper, Step, StepLabel, StepContent, Chip } from '@mui/material';

const SequenceDisplay = ({ sequence }) => {
  if (!sequence || !sequence.steps) return null;

  return (
    <Box sx={{ width: '100%', p: 2 }}>
      {/* Metadata Section */}
      <Card sx={{ mb: 3, backgroundColor: '#f5f5f5' }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Sequence Details
          </Typography>
          <Typography variant="body1">
            Role: {sequence.metadata.role}
          </Typography>
          <Typography variant="body1">
            Industry: {sequence.metadata.industry}
          </Typography>
          <Typography variant="body1">
            Seniority: {sequence.metadata.seniority}
          </Typography>
          <Typography variant="body1">
            Company Type: {sequence.metadata.company_type}
          </Typography>
        </CardContent>
      </Card>

      {/* Steps Section */}
      <Stepper orientation="vertical">
        {sequence.steps.map((step) => (
          <Step key={step.id} active={true}>
            <StepLabel>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Typography variant="subtitle1">
                  Step {step.id}
                </Typography>
                <Chip 
                  label={step.type} 
                  color={
                    step.type === 'email' ? 'primary' :
                    step.type === 'linkedin' ? 'info' :
                    step.type === 'call' ? 'success' : 'default'
                  }
                  size="small"
                />
                <Chip 
                  label={`${step.delay} days`} 
                  variant="outlined" 
                  size="small"
                />
              </Box>
            </StepLabel>
            <StepContent>
              <Card variant="outlined" sx={{ mt: 1, mb: 2 }}>
                <CardContent>
                  <Typography variant="body1" gutterBottom>
                    {step.content}
                  </Typography>
                  <Typography variant="subtitle2" color="textSecondary" sx={{ mt: 1 }}>
                    Personalization Tips:
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    {step.personalization_tips}
                  </Typography>
                </CardContent>
              </Card>
            </StepContent>
          </Step>
        ))}
      </Stepper>
    </Box>
  );
};

export default SequenceDisplay; 