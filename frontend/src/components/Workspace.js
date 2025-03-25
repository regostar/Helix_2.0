import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  MenuItem,
  IconButton,
  Tooltip,
  Divider
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import CloseIcon from '@mui/icons-material/Close';
import SequenceDisplay from './SequenceDisplay';

function Workspace({ sequence, onSequenceUpdate }) {
  const [openDialog, setOpenDialog] = useState(false);
  const [editingStep, setEditingStep] = useState(null);
  const [parsedSequence, setParsedSequence] = useState(null);
  const [newStep, setNewStep] = useState({
    type: 'email',
    content: '',
    delay: 0,
    personalization_tips: '',
  });

  console.log('Workspace received sequence:', sequence);

  useEffect(() => {
    console.log('Workspace useEffect - sequence changed:', sequence);
    // Parse the sequence if it's a string
    if (typeof sequence === 'string') {
      try {
        console.log('Parsing string sequence');
        const parsed = JSON.parse(sequence);
        console.log('Parsed sequence:', parsed);
        
        // Handle the nested structure
        if (parsed.tool_result) {
          console.log('Found tool_result, parsing:', parsed.tool_result);
          const toolResult = JSON.parse(parsed.tool_result);
          setParsedSequence(toolResult);
        } else if (parsed.metadata && parsed.steps) {
          console.log('Found direct sequence data');
          setParsedSequence(parsed);
        } else {
          console.error('Invalid sequence data structure:', parsed);
        }
      } catch (e) {
        console.error('Error parsing sequence:', e, 'Raw sequence:', sequence);
      }
    } else if (sequence && typeof sequence === 'object') {
      console.log('Using object sequence directly:', sequence);
      setParsedSequence(sequence);
    } else {
      console.log('No sequence data received');
    }
  }, [sequence]);

  const handleOpenDialog = (step) => {
    if (step) {
      setEditingStep(step);
      setNewStep(step);
    } else {
      setEditingStep(null);
      setNewStep({
        type: 'email',
        content: '',
        delay: 0,
        personalization_tips: '',
      });
    }
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
    setEditingStep(null);
    setNewStep({
      type: 'email',
      content: '',
      delay: 0,
      personalization_tips: '',
    });
  };

  const handleSaveStep = () => {
    if (!newStep.content) return;

    let updatedSteps;
    if (editingStep) {
      updatedSteps = parsedSequence.steps.map((step) =>
        step.id === editingStep.id ? { ...newStep, id: step.id } : step
      );
    } else {
      updatedSteps = [...(parsedSequence?.steps || []), { ...newStep, id: Date.now().toString() }];
    }

    // Call the parent's onSequenceUpdate with the updated steps
    if (typeof onSequenceUpdate === 'function') {
      try {
        onSequenceUpdate(updatedSteps);
        console.log('Sequence updated with new steps:', updatedSteps);
      } catch (error) {
        console.error('Error updating sequence:', error);
      }
    } else {
      console.warn('onSequenceUpdate is not provided or not a function');
    }

    handleCloseDialog();
  };

  const handleStepUpdate = (updatedSteps) => {
    console.log('Workspace received step update:', updatedSteps);
    
    // Call the parent's onSequenceUpdate with the updated steps
    if (typeof onSequenceUpdate === 'function') {
      try {
        onSequenceUpdate(updatedSteps);
        console.log('Sequence updated through SequenceDisplay');
      } catch (error) {
        console.error('Error updating sequence from SequenceDisplay:', error);
      }
    } else {
      console.warn('onSequenceUpdate is not provided or not a function');
    }
  };

  return (
    <Box sx={{ 
      flexGrow: 1, 
      display: 'flex', 
      flexDirection: 'column',
      height: '100%',
      overflow: 'hidden'
    }}>
      <Box sx={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        px: 3,
        py: 2,
        borderBottom: '1px solid',
        borderColor: 'divider'
      }}>
        <Typography variant="h6" sx={{ fontWeight: 600 }}>
          Recruiting Sequence
        </Typography>
        <Tooltip title="Add new step">
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => handleOpenDialog()}
            size="small"
            disableElevation
          >
            Add Step
          </Button>
        </Tooltip>
      </Box>
      
      <Box sx={{ 
        flexGrow: 1, 
        overflow: 'auto',
        p: 3
      }}>
        {parsedSequence ? (
          <SequenceDisplay sequence={parsedSequence} onStepUpdate={handleStepUpdate} />
        ) : (
          <Box sx={{ 
            height: '100%', 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center',
            flexDirection: 'column',
            gap: 2,
            color: 'text.secondary'
          }}>
            <Typography variant="h6">No Sequence Available</Typography>
            <Typography variant="body2">
              Create a new recruiting sequence using the chat assistant.
            </Typography>
          </Box>
        )}
      </Box>

      <Dialog 
        open={openDialog} 
        onClose={handleCloseDialog} 
        maxWidth="sm" 
        fullWidth
        PaperProps={{
          elevation: 0,
          sx: { 
            borderRadius: 2,
            border: '1px solid',
            borderColor: 'divider'
          }
        }}
      >
        <DialogTitle sx={{ 
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center', 
          pb: 1
        }}>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            {editingStep ? 'Edit Step' : 'Add New Step'}
          </Typography>
          <IconButton size="small" onClick={handleCloseDialog} aria-label="close">
            <CloseIcon fontSize="small" />
          </IconButton>
        </DialogTitle>
        <Divider />
        <DialogContent sx={{ pt: 3 }}>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2.5 }}>
            <TextField
              select
              label="Type"
              value={newStep.type}
              onChange={(e) => setNewStep({ ...newStep, type: e.target.value })}
              fullWidth
              variant="outlined"
              sx={{ 
                '& .MuiOutlinedInput-root': {
                  borderRadius: 1.5,
                }
              }}
            >
              <MenuItem value="email">Email</MenuItem>
              <MenuItem value="linkedin">LinkedIn Message</MenuItem>
              <MenuItem value="call">Phone Call</MenuItem>
              <MenuItem value="meeting">Meeting</MenuItem>
              <MenuItem value="other">Other</MenuItem>
            </TextField>
            <TextField
              label="Content"
              multiline
              rows={4}
              value={newStep.content}
              onChange={(e) => setNewStep({ ...newStep, content: e.target.value })}
              fullWidth
              variant="outlined"
              placeholder="Enter the message content for this step..."
              sx={{ 
                '& .MuiOutlinedInput-root': {
                  borderRadius: 1.5,
                }
              }}
            />
            <TextField
              label="Delay (days)"
              type="number"
              value={newStep.delay}
              onChange={(e) =>
                setNewStep({ ...newStep, delay: parseInt(e.target.value) || 0 })
              }
              fullWidth
              variant="outlined"
              helperText="Number of days to wait after the previous step"
              sx={{ 
                '& .MuiOutlinedInput-root': {
                  borderRadius: 1.5,
                }
              }}
            />
            <TextField
              label="Personalization Tips"
              multiline
              rows={2}
              value={newStep.personalization_tips}
              onChange={(e) =>
                setNewStep({ ...newStep, personalization_tips: e.target.value })
              }
              fullWidth
              variant="outlined"
              placeholder="Add tips for personalizing this message..."
              sx={{ 
                '& .MuiOutlinedInput-root': {
                  borderRadius: 1.5,
                }
              }}
            />
          </Box>
        </DialogContent>
        <DialogActions sx={{ px: 3, py: 2 }}>
          <Button 
            onClick={handleCloseDialog} 
            variant="outlined"
            sx={{ textTransform: 'none', borderRadius: 1.5 }}
          >
            Cancel
          </Button>
          <Button 
            onClick={handleSaveStep} 
            variant="contained" 
            color="primary"
            disableElevation
            disabled={!newStep.content}
            sx={{ textTransform: 'none', borderRadius: 1.5 }}
          >
            Save
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default Workspace; 