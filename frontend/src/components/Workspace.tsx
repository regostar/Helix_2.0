import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  IconButton,
  TextField,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Divider,
  Chip,
  Tab,
  Tabs,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import EmailIcon from '@mui/icons-material/Email';
import LinkedIn from '@mui/icons-material/LinkedIn';

interface SequenceStep {
  id: string;
  type: string;
  content: string;
  delay: number;
  personalization_tips?: string;
}

interface SequenceMetadata {
  role: string;
  industry: string;
  seniority: string;
  company_type: string;
  generated_at: string;
}

interface Sequence {
  metadata: SequenceMetadata;
  steps: SequenceStep[];
}

interface Candidate {
  name: string;
  email: string;
  role?: string;
  experience?: string;
  skills?: string;
  linkedin?: string;
  [key: string]: any;
}

interface WorkspaceProps {
  sequence: Sequence | null;
  onSequenceUpdate: (steps: SequenceStep[]) => void;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`tabpanel-${index}`}
      aria-labelledby={`tab-${index}`}
      {...other}
      style={{ height: '100%', overflow: 'auto' }}
    >
      {value === index && (
        <Box sx={{ p: 3, height: '100%' }}>
          {children}
        </Box>
      )}
    </div>
  );
}

const Workspace: React.FC<WorkspaceProps> = ({ sequence, onSequenceUpdate }) => {
  const [tabValue, setTabValue] = useState(0);
  const [openDialog, setOpenDialog] = useState(false);
  const [editingStep, setEditingStep] = useState<SequenceStep | null>(null);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [newStep, setNewStep] = useState<SequenceStep>({
    id: Date.now().toString(),
    type: 'email',
    content: '',
    delay: 0,
    personalization_tips: ''
  });
  const [emailTemplate, setEmailTemplate] = useState('');
  const [selectedCandidate, setSelectedCandidate] = useState<Candidate | null>(null);
  const [openEmailDialog, setOpenEmailDialog] = useState(false);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleOpenDialog = (step?: SequenceStep) => {
    if (step) {
      setEditingStep(step);
      setNewStep(step);
    } else {
      setEditingStep(null);
      setNewStep({
        id: Date.now().toString(),
        type: 'email',
        content: '',
        delay: 0,
        personalization_tips: ''
      });
    }
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
    setEditingStep(null);
    setNewStep({
      id: Date.now().toString(),
      type: 'email',
      content: '',
      delay: 0,
      personalization_tips: ''
    });
  };

  const handleSaveStep = () => {
    if (!newStep.content || !sequence) return;

    const updatedSteps = editingStep
      ? sequence.steps.map((step) =>
          step.id === editingStep.id
            ? { ...step, ...newStep }
            : step
        )
      : [...sequence.steps, { ...newStep, id: Date.now().toString() }];

    onSequenceUpdate(updatedSteps);
    handleCloseDialog();
  };

  const handleDeleteStep = (id: string) => {
    if (!sequence) return;
    onSequenceUpdate(sequence.steps.filter((step) => step.id !== id));
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files.length > 0) {
      setCsvFile(event.target.files[0]);
    }
  };

  const handleFileUpload = () => {
    if (!csvFile) return;
    
    // Simulate CSV upload and processing
    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target?.result as string;
      const lines = text.split('\n');
      const headers = lines[0].split(',').map(h => h.trim());
      
      const parsedCandidates: Candidate[] = [];
      for (let i = 1; i < lines.length; i++) {
        if (!lines[i].trim()) continue;
        
        const values = lines[i].split(',').map(v => v.trim());
        const candidate: Candidate = { name: '', email: '' };
        
        headers.forEach((header, index) => {
          if (index < values.length) {
            candidate[header.toLowerCase()] = values[index];
          }
        });
        
        if (candidate.name && candidate.email) {
          parsedCandidates.push(candidate);
        }
      }
      
      setCandidates(parsedCandidates);
    };
    reader.readAsText(csvFile);
  };

  const handleOpenEmailDialog = (candidate: Candidate) => {
    setSelectedCandidate(candidate);
    
    // If we have a sequence, use the first email step as template
    if (sequence) {
      const emailStep = sequence.steps.find(s => s.type === 'email');
      if (emailStep) {
        setEmailTemplate(emailStep.content);
      }
    }
    
    setOpenEmailDialog(true);
  };

  const handleSendEmail = () => {
    // Simulate sending email
    alert(`Email would be sent to ${selectedCandidate?.email}`);
    setOpenEmailDialog(false);
  };

  const previewPersonalizedEmail = () => {
    if (!selectedCandidate || !emailTemplate) return emailTemplate;
    
    let personalized = emailTemplate;
    Object.entries(selectedCandidate).forEach(([key, value]) => {
      personalized = personalized.replace(new RegExp(`{${key}}`, 'g'), value);
    });
    
    return personalized;
  };

  // Render empty state if no sequence
  if (!sequence) {
    return (
      <Box sx={{ flexGrow: 1, p: 3, overflow: 'auto' }}>
        <Paper sx={{ height: '100%', p: 3, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Typography variant="h6" color="text.secondary">
            No sequence generated yet. Start a conversation to create one.
          </Typography>
        </Paper>
      </Box>
    );
  }

  return (
    <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={tabValue} onChange={handleTabChange} aria-label="workspace tabs">
          <Tab label="Sequence" />
          <Tab label="Candidates" />
          <Tab label="Outreach" />
        </Tabs>
      </Box>
      
      <TabPanel value={tabValue} index={0}>
        <Paper sx={{ height: '100%', p: 3 }}>
          {/* Metadata Section */}
          <Box sx={{ mb: 3 }}>
            <Typography variant="h5" gutterBottom>Recruiting Sequence</Typography>
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 2 }}>
              <Chip label={`Role: ${sequence.metadata.role}`} color="primary" />
              <Chip label={`Industry: ${sequence.metadata.industry}`} />
              <Chip label={`Seniority: ${sequence.metadata.seniority}`} />
              <Chip label={`Company: ${sequence.metadata.company_type}`} />
            </Box>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={() => handleOpenDialog()}
            >
              Add Step
            </Button>
          </Box>

          <List>
            {sequence.steps.map((step, index) => (
              <React.Fragment key={step.id}>
                <ListItem>
                  <ListItemText
                    primary={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography variant="subtitle1">
                          Step {index + 1}: {step.type}
                        </Typography>
                        {step.delay > 0 && (
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                            <AccessTimeIcon fontSize="small" />
                            <Typography variant="caption">
                              {step.delay} days
                            </Typography>
                          </Box>
                        )}
                      </Box>
                    }
                    secondary={
                      <Box>
                        <Typography variant="body2">{step.content}</Typography>
                        {step.personalization_tips && (
                          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
                            Personalization Tips: {step.personalization_tips}
                          </Typography>
                        )}
                      </Box>
                    }
                  />
                  <ListItemSecondaryAction>
                    <IconButton
                      edge="end"
                      onClick={() => handleOpenDialog(step)}
                      sx={{ mr: 1 }}
                    >
                      <EditIcon />
                    </IconButton>
                    <IconButton
                      edge="end"
                      onClick={() => handleDeleteStep(step.id)}
                    >
                      <DeleteIcon />
                    </IconButton>
                  </ListItemSecondaryAction>
                </ListItem>
                {index < sequence.steps.length - 1 && <Divider />}
              </React.Fragment>
            ))}
          </List>
        </Paper>
      </TabPanel>
      
      <TabPanel value={tabValue} index={1}>
        <Paper sx={{ height: '100%', p: 3 }}>
          <Typography variant="h5" gutterBottom>Candidate Management</Typography>
          
          <Box sx={{ mb: 3, display: 'flex', alignItems: 'center', gap: 2 }}>
            <Button
              variant="contained"
              component="label"
              startIcon={<UploadFileIcon />}
            >
              Upload CSV
              <input
                type="file"
                accept=".csv"
                hidden
                onChange={handleFileChange}
              />
            </Button>
            {csvFile && (
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Typography variant="body2">
                  {csvFile.name}
                </Typography>
                <Button 
                  variant="outlined" 
                  size="small"
                  onClick={handleFileUpload}
                >
                  Process
                </Button>
              </Box>
            )}
          </Box>
          
          {candidates.length > 0 ? (
            <TableContainer component={Paper} sx={{ maxHeight: 'calc(100% - 100px)' }}>
              <Table stickyHeader>
                <TableHead>
                  <TableRow>
                    <TableCell>Name</TableCell>
                    <TableCell>Email</TableCell>
                    <TableCell>Role</TableCell>
                    <TableCell>Experience</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {candidates.map((candidate, index) => (
                    <TableRow key={index}>
                      <TableCell>{candidate.name}</TableCell>
                      <TableCell>{candidate.email}</TableCell>
                      <TableCell>{candidate.role || 'N/A'}</TableCell>
                      <TableCell>{candidate.experience || 'N/A'}</TableCell>
                      <TableCell>
                        <IconButton
                          size="small"
                          onClick={() => handleOpenEmailDialog(candidate)}
                          title="Send Email"
                        >
                          <EmailIcon fontSize="small" />
                        </IconButton>
                        <IconButton
                          size="small"
                          title="LinkedIn Message"
                        >
                          <LinkedIn fontSize="small" />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          ) : (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '200px' }}>
              <Typography variant="body1" color="text.secondary">
                Upload a CSV file to load candidates
              </Typography>
            </Box>
          )}
        </Paper>
      </TabPanel>
      
      <TabPanel value={tabValue} index={2}>
        <Paper sx={{ height: '100%', p: 3 }}>
          <Typography variant="h5" gutterBottom>Outreach Dashboard</Typography>
          
          <Box sx={{ mt: 2 }}>
            <Typography variant="h6" gutterBottom>Campaign Status</Typography>
            <Box sx={{ display: 'flex', gap: 3, mb: 4 }}>
              <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
                <Typography variant="h4">{candidates.length}</Typography>
                <Typography variant="body2">Total Candidates</Typography>
              </Box>
              <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
                <Typography variant="h4">0</Typography>
                <Typography variant="body2">Emails Sent</Typography>
              </Box>
              <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
                <Typography variant="h4">0</Typography>
                <Typography variant="body2">Responses</Typography>
              </Box>
            </Box>
            
            <Typography variant="h6" gutterBottom>Upcoming Outreach</Typography>
            <Typography variant="body1" color="text.secondary">
              No scheduled outreach. Configure the sequence and load candidates to begin.
            </Typography>
          </Box>
        </Paper>
      </TabPanel>
      
      {/* Step Dialog */}
      <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle>
          {editingStep ? 'Edit Step' : 'Add New Step'}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              select
              label="Type"
              value={newStep.type}
              onChange={(e) => setNewStep({ ...newStep, type: e.target.value })}
              fullWidth
              SelectProps={{
                native: true,
              }}
            >
              <option value="email">Email</option>
              <option value="linkedin">LinkedIn Message</option>
              <option value="call">Phone Call</option>
              <option value="meeting">Meeting</option>
            </TextField>
            <TextField
              label="Content"
              multiline
              rows={4}
              value={newStep.content}
              onChange={(e) => setNewStep({ ...newStep, content: e.target.value })}
              fullWidth
              helperText="Use {name}, {role}, etc. as placeholders for personalization"
            />
            <TextField
              label="Delay (days)"
              type="number"
              value={newStep.delay}
              onChange={(e) =>
                setNewStep({ ...newStep, delay: parseInt(e.target.value) || 0 })
              }
              fullWidth
            />
            <TextField
              label="Personalization Tips"
              multiline
              rows={2}
              value={newStep.personalization_tips || ''}
              onChange={(e) =>
                setNewStep({ ...newStep, personalization_tips: e.target.value })
              }
              fullWidth
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button onClick={handleSaveStep} variant="contained">
            Save
          </Button>
        </DialogActions>
      </Dialog>
      
      {/* Email Dialog */}
      <Dialog open={openEmailDialog} onClose={() => setOpenEmailDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>
          Send Personalized Email
        </DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              label="To"
              value={selectedCandidate?.email || ''}
              InputProps={{
                readOnly: true,
              }}
              fullWidth
            />
            <TextField
              label="Subject"
              defaultValue={`Opportunity for ${selectedCandidate?.name || 'Candidate'}`}
              fullWidth
            />
            <TextField
              label="Email Template"
              multiline
              rows={4}
              value={emailTemplate}
              onChange={(e) => setEmailTemplate(e.target.value)}
              fullWidth
              helperText="Use {name}, {role}, {experience}, etc. as placeholders"
            />
            <Typography variant="subtitle1">Preview:</Typography>
            <Paper variant="outlined" sx={{ p: 2, bgcolor: 'background.default' }}>
              <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
                {previewPersonalizedEmail()}
              </Typography>
            </Paper>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenEmailDialog(false)}>Cancel</Button>
          <Button onClick={handleSendEmail} variant="contained" startIcon={<EmailIcon />}>
            Send Email
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Workspace; 