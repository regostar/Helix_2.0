import React, { useState, useRef, useEffect } from 'react';
import { 
  Box, 
  Card, 
  CardContent, 
  Typography, 
  Stepper, 
  Step, 
  StepLabel, 
  StepContent, 
  Chip,
  IconButton,
  TextField,
  Snackbar,
  Alert,
  Badge,
  Paper,
  Grid,
  Tooltip,
  Avatar
} from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import SaveIcon from '@mui/icons-material/Save';
import CancelIcon from '@mui/icons-material/Cancel';
import DeleteIcon from '@mui/icons-material/Delete';
import EmailOutlinedIcon from '@mui/icons-material/EmailOutlined';
import LinkedInIcon from '@mui/icons-material/LinkedIn';
import CallOutlinedIcon from '@mui/icons-material/CallOutlined';
import EventOutlinedIcon from '@mui/icons-material/EventOutlined';
import MoreTimeIcon from '@mui/icons-material/MoreTime';
import { alpha } from '@mui/material/styles';
import { useSocket } from './SocketContext';

/**
 * SequenceDisplay Component
 * @param {Object} props
 * @param {Object} props.sequence - The sequence to display
 * @param {Object} props.sequence.metadata - Metadata about the sequence
 * @param {Array} props.sequence.steps - Steps in the sequence
 * @param {Function} [props.onStepUpdate] - Optional callback when steps are updated
 */
const SequenceDisplay = ({ sequence, onStepUpdate = () => {} }) => {
  const [editableSteps, setEditableSteps] = useState({});
  const [editingStepId, setEditingStepId] = useState(null);
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');
  const [snackbarSeverity, setSnackbarSeverity] = useState('info');
  const textFieldRef = useRef(null);
  const { socket, isConnected, emit } = useSocket();

  console.log('SequenceDisplay rendered with sequence:', sequence);

  // Initialize editableSteps whenever sequence changes
  useEffect(() => {
    if (sequence && sequence.steps) {
      console.log('SequenceDisplay - sequence changed, steps:', sequence.steps);
      const initialEditableSteps = {};
      sequence.steps.forEach(step => {
        initialEditableSteps[step.id] = step.content;
      });
      setEditableSteps(initialEditableSteps);
      console.log('SequenceDisplay - Initialized editable steps:', initialEditableSteps);
    } else {
      console.warn('SequenceDisplay - Received invalid sequence data:', sequence);
    }
  }, [sequence]);

  if (!sequence) {
    console.warn('SequenceDisplay - No sequence provided');
    return (
      <Box sx={{ p: 4, textAlign: 'center' }}>
        <Typography variant="body1" color="text.secondary">
          No sequence data available. Create a new sequence to get started.
        </Typography>
      </Box>
    );
  }

  if (!sequence.steps || !Array.isArray(sequence.steps) || sequence.steps.length === 0) {
    console.warn('SequenceDisplay - No steps in sequence:', sequence);
    return (
      <Box sx={{ p: 4, textAlign: 'center' }}>
        <Typography variant="body1" color="text.secondary">
          This sequence doesn't have any steps yet. Add some steps to get started.
        </Typography>
      </Box>
    );
  }

  if (!sequence.metadata) {
    console.warn('SequenceDisplay - No metadata in sequence:', sequence);
    return (
      <Box sx={{ p: 4, textAlign: 'center' }}>
        <Typography variant="body1" color="text.secondary">
          Sequence is missing metadata. Please regenerate the sequence.
        </Typography>
      </Box>
    );
  }

  const showSnackbar = (message, severity = 'info') => {
    setSnackbarMessage(message);
    setSnackbarSeverity(severity);
    setSnackbarOpen(true);
  };

  const handleSnackbarClose = () => {
    setSnackbarOpen(false);
  };

  const handleEditClick = (stepId, content) => {
    setEditableSteps({
      ...editableSteps,
      [stepId]: content
    });
    setEditingStepId(stepId);
    
    // Focus on the text field after a short delay
    setTimeout(() => {
      if (textFieldRef.current) {
        textFieldRef.current.focus();
      }
    }, 100);
  };

  const handleContentChange = (stepId, newContent) => {
    setEditableSteps({
      ...editableSteps,
      [stepId]: newContent
    });
  };

  const handleSaveClick = (stepId) => {
    const updatedStep = sequence.steps.find(step => step.id === stepId);
    if (!updatedStep) return;
    
    const newSteps = sequence.steps.map(step => 
      step.id === stepId 
        ? { ...step, content: editableSteps[stepId] }
        : step
    );
    
    console.log('SequenceDisplay - saving edits:', newSteps);
    
    // Check if onStepUpdate is provided and is a function before calling it
    if (typeof onStepUpdate === 'function') {
      try {
        onStepUpdate(newSteps);
        console.log('onStepUpdate called successfully');
      } catch (error) {
        console.error('Error calling onStepUpdate:', error);
        showSnackbar('Error updating sequence', 'error');
      }
    } else {
      console.warn('onStepUpdate is not a function or not provided');
      showSnackbar('Could not update sequence', 'warning');
    }
    
    setEditingStepId(null);
    
    // Send to backend for processing via socket
    try {
      if (isConnected) {
        // First, emit the direct edit_sequence_step event to update the database
        const editData = {
          step_id: stepId,
          new_content: editableSteps[stepId]
        };
        
        const editSuccess = emit('edit_sequence_step', editData);
        
        if (editSuccess) {
          console.log('Edit sequence step event emitted successfully');
          
          // Then, send for AI refinement
          const refinementData = {
            step_id: stepId,
            content: editableSteps[stepId],
            request: "Refine this step based on the edits to make it more effective"
          };
          
          const refinementSuccess = emit('process_edit', refinementData);
          
          if (refinementSuccess) {
            console.log('Process edit event emitted successfully');
            showSnackbar('Changes saved and being refined by AI', 'success');
          } else {
            console.warn('Failed to emit process_edit event');
            showSnackbar('Changes saved but AI refinement failed', 'warning');
          }
        } else {
          throw new Error('Failed to emit edit_sequence_step event');
        }
      } else {
        console.warn('Socket is not connected');
        showSnackbar('Changes saved but AI refinement unavailable - socket disconnected', 'warning');
      }
    } catch (error) {
      console.error('Error emitting socket events:', error);
      showSnackbar('Error connecting to AI service', 'error');
    }
  };

  const handleCancelClick = () => {
    setEditingStepId(null);
  };

  const handleDeleteClick = (stepId) => {
    const newSteps = sequence.steps.filter(step => step.id !== stepId);
    
    console.log('SequenceDisplay - deleting step:', stepId);
    
    // Check if onStepUpdate is provided and is a function before calling it
    if (typeof onStepUpdate === 'function') {
      try {
        onStepUpdate(newSteps);
        console.log('onStepUpdate called successfully for delete');
        showSnackbar('Step deleted successfully', 'success');
      } catch (error) {
        console.error('Error calling onStepUpdate for delete:', error);
        showSnackbar('Error deleting step', 'error');
      }
    } else {
      console.warn('onStepUpdate is not a function or not provided');
      showSnackbar('Could not delete step', 'warning');
    }
  };

  // Get step icon based on type
  const getStepIcon = (type) => {
    switch(type) {
      case 'email':
        return <EmailOutlinedIcon />;
      case 'linkedin':
        return <LinkedInIcon />;
      case 'call':
        return <CallOutlinedIcon />;
      case 'meeting':
        return <EventOutlinedIcon />;
      default:
        return <MoreTimeIcon />;
    }
  };

  // Get step color based on type
  const getStepColor = (type) => {
    switch(type) {
      case 'email':
        return '#2563eb'; // blue
      case 'linkedin':
        return '#0077b5'; // LinkedIn blue
      case 'call':
        return '#10b981'; // green
      case 'meeting':
        return '#8b5cf6'; // purple
      default:
        return '#6b7280'; // gray
    }
  };

  return (
    <Box sx={{ width: '100%' }}>
      {/* Metadata Section */}
      <Card 
        sx={{ 
          mb: 4, 
          borderRadius: 2,
          background: 'linear-gradient(to right, #f1f5f9, #f8fafc)',
          boxShadow: 'none',
          border: '1px solid #e2e8f0'
        }}
      >
        <CardContent>
          <Typography variant="h5" gutterBottom sx={{ fontWeight: 'medium' }}>
            {sequence.metadata.role} Recruiting Sequence
          </Typography>
          
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={6} md={3}>
              <Typography variant="body2" color="text.secondary">
                Industry
              </Typography>
              <Typography variant="body1" gutterBottom>
                {sequence.metadata.industry}
              </Typography>
            </Grid>
            <Grid item xs={6} md={3}>
              <Typography variant="body2" color="text.secondary">
                Seniority
              </Typography>
              <Typography variant="body1" gutterBottom>
                {sequence.metadata.seniority}
              </Typography>
            </Grid>
            <Grid item xs={6} md={3}>
              <Typography variant="body2" color="text.secondary">
                Company Type
              </Typography>
              <Typography variant="body1" gutterBottom>
                {sequence.metadata.company_type || 'Any'}
              </Typography>
            </Grid>
            <Grid item xs={6} md={3}>
              <Typography variant="body2" color="text.secondary">
                Generated
              </Typography>
              <Typography variant="body1" gutterBottom>
                {new Date(sequence.metadata.generated_at).toLocaleDateString()}
              </Typography>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Steps Section */}
      <Stepper orientation="vertical" sx={{ ml: -1 }}>
        {sequence.steps.map((step, index) => {
          const stepColor = getStepColor(step.type);
          return (
            <Step key={step.id} active={true}>
              <StepLabel 
                StepIconComponent={() => (
                  <CustomAvatar sx={{ 
                    bgcolor: alpha(stepColor, 0.1), 
                    color: stepColor,
                    width: 36,
                    height: 36
                  }}>
                    {getStepIcon(step.type)}
                  </CustomAvatar>
                )}
              >
                <Box sx={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'space-between',
                  gap: 1,
                  pr: 1,
                  py: 0.5
                }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography variant="subtitle1" sx={{ fontWeight: 500 }}>
                      Step {index + 1}
                    </Typography>
                    <Chip 
                      label={step.type} 
                      size="small"
                      sx={{ 
                        bgcolor: alpha(stepColor, 0.1), 
                        color: stepColor,
                        fontWeight: 500,
                        borderRadius: '4px'
                      }}
                    />
                  </Box>
                  <Chip 
                    icon={<MoreTimeIcon fontSize="small" />}
                    label={`${step.delay} days`} 
                    variant="outlined" 
                    size="small"
                    sx={{ borderRadius: '4px' }}
                  />
                </Box>
              </StepLabel>
              <StepContent>
                <Card 
                  variant="outlined" 
                  sx={{ 
                    mt: 1, 
                    mb: 2, 
                    borderRadius: 1.5,
                    borderColor: '#e2e8f0',
                    boxShadow: 'none'
                  }}
                >
                  <CardContent sx={{ position: 'relative', pb: 1 }}>
                    {editingStepId === step.id ? (
                      <Box>
                        <TextField
                          inputRef={textFieldRef}
                          multiline
                          fullWidth
                          variant="outlined"
                          value={editableSteps[step.id]}
                          onChange={(e) => handleContentChange(step.id, e.target.value)}
                          sx={{ 
                            mb: 2,
                            '& .MuiOutlinedInput-root': {
                              borderRadius: 1.5,
                            }
                          }}
                        />
                        <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1 }}>
                          <Tooltip title="Save changes">
                            <IconButton 
                              size="small" 
                              color="primary" 
                              onClick={() => handleSaveClick(step.id)}
                            >
                              <SaveIcon />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Cancel editing">
                            <IconButton 
                              size="small" 
                              onClick={handleCancelClick}
                            >
                              <CancelIcon />
                            </IconButton>
                          </Tooltip>
                        </Box>
                      </Box>
                    ) : (
                      <>
                        <Typography 
                          variant="body1" 
                          gutterBottom
                          sx={{ lineHeight: 1.6, pr: 6 }}
                        >
                          {step.content}
                        </Typography>
                        <Box sx={{ position: 'absolute', top: 10, right: 10, display: 'flex' }}>
                          <Tooltip title="Edit message">
                            <IconButton 
                              size="small"
                              onClick={() => handleEditClick(step.id, step.content)}
                              sx={{ color: 'text.secondary' }}
                            >
                              <EditIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Delete step">
                            <IconButton 
                              size="small"
                              onClick={() => handleDeleteClick(step.id)}
                              sx={{ color: 'text.secondary' }}
                            >
                              <DeleteIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        </Box>
                      </>
                    )}
                    
                    {step.personalization_tips && (
                      <Paper 
                        variant="outlined" 
                        sx={{ 
                          mt: 2, 
                          p: 1.5, 
                          bgcolor: alpha('#f8fafc', 0.8),
                          borderColor: '#e2e8f0',
                          borderRadius: 1,
                        }}
                      >
                        <Typography 
                          variant="subtitle2" 
                          color="text.secondary" 
                          sx={{ fontWeight: 500, mb: 0.5 }}
                        >
                          Personalization Tips
                        </Typography>
                        <Typography 
                          variant="body2" 
                          color="text.secondary"
                          sx={{ lineHeight: 1.5 }}
                        >
                          {step.personalization_tips}
                        </Typography>
                      </Paper>
                    )}
                  </CardContent>
                </Card>
              </StepContent>
            </Step>
          );
        })}
      </Stepper>

      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbarOpen}
        autoHideDuration={6000}
        onClose={handleSnackbarClose}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert 
          onClose={handleSnackbarClose} 
          severity={snackbarSeverity} 
          sx={{ 
            width: '100%',
            boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)'
          }}
        >
          {snackbarMessage}
        </Alert>
      </Snackbar>
    </Box>
  );
};

// Missing Avatar component import
const CustomAvatar = ({ children, sx = {} }) => {
  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: 28,
        height: 28,
        borderRadius: '50%',
        ...sx
      }}
    >
      {children}
    </Box>
  );
};

export default SequenceDisplay; 